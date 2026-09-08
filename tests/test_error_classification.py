"""Tests for the polling error classifier and the NPSSO auth probe."""

import socket

import pytest
import requests

psnawp_exceptions = pytest.importorskip("psnawp_api.core.psnawp_exceptions")


# Builds an exception whose cause chain ends in the supplied root error
def chained(root, depth=2):
    current = root
    for level in range(depth):
        try:
            raise RuntimeError(f"wrapper level {level}") from current
        except RuntimeError as wrapper:
            current = wrapper
    return current


# Verifies an expired or rejected NPSSO is classified as an auth failure, which is the only case worth alerting on immediately
@pytest.mark.parametrize("message", [
    "Your npsso code has expired",
    "Something went wrong while authenticating",
    "invalid_grant returned by /authz/v3/oauth/token",
    "Invalid npsso supplied",
    "GET /authz/v3/oauth/token returned 401 Unauthorized",
])
def test_authentication_failures_are_classified_as_auth(pm_module, message):
    assert pm_module.classify_psn_exception(Exception(message)) == "auth"


# Verifies the library's own authentication error is recognized wherever it sits in the cause chain
def test_library_authentication_error_is_recognized_through_the_chain(pm_module):
    root = psnawp_exceptions.PSNAWPAuthenticationError("token refused")

    assert pm_module.classify_psn_exception(chained(root)) == "auth"


@pytest.mark.parametrize("root", [
    requests.exceptions.ConnectionError("connection reset"),
    requests.exceptions.Timeout("read timed out"),
    requests.exceptions.SSLError("handshake failure"),
    requests.exceptions.ChunkedEncodingError("truncated body"),
    ConnectionResetError("peer went away"),
    TimeoutError("no response"),
])
# Verifies network hiccups are classified as transient so the tool retries quietly instead of alerting
def test_network_failures_are_classified_as_transient(pm_module, root):
    assert pm_module.classify_psn_exception(chained(root)) == "transient"


@pytest.mark.parametrize("message", [
    "Remote end closed connection without response",
    "Connection reset by peer",
    "Connection aborted",
    "Read timed out",
    "Service temporarily unavailable",
])
# Verifies a transient failure that arrives only as text is still treated as transient
def test_transient_failures_without_a_type_are_recognized_by_message(pm_module, message):
    assert pm_module.classify_psn_exception(Exception(message)) == "transient"


# Verifies an unexpected response shape is classified as malformed so the session is recreated
def test_malformed_response_is_classified_as_malformed(pm_module):
    root = pm_module.PsnMalformedResponse("onlineStatus is empty")

    assert pm_module.classify_psn_exception(chained(root)) == "malformed"


@pytest.mark.parametrize("root", [AttributeError("'NoneType' object has no attribute 'get'"), TypeError("string indices must be integers")])
# Verifies the attribute and type errors a changed payload produces are treated as malformed, not unknown
def test_payload_shape_errors_fall_back_to_malformed(pm_module, root):
    assert pm_module.classify_psn_exception(chained(root)) == "malformed"


@pytest.mark.parametrize("root", [
    OSError(24, "Too many open files"),
    Exception("OSError(24, 'Too many open files')"),
    Exception("[Errno 24] Too many open files"),
])
# Verifies local file descriptor exhaustion is separated from PSN problems, since only the operator can fix it
def test_file_descriptor_exhaustion_is_classified_as_exhausted(pm_module, root):
    assert pm_module.classify_psn_exception(chained(root)) == "exhausted"
    assert pm_module.is_too_many_open_files(chained(root)) is True


# Verifies an unrelated OS error is not mistaken for descriptor exhaustion
def test_other_os_errors_are_not_treated_as_exhaustion(pm_module):
    assert pm_module.is_too_many_open_files(OSError(2, "No such file or directory")) is False


# Verifies descriptor exhaustion outranks an auth message, because retrying auth cannot fix a local limit
def test_exhaustion_outranks_an_auth_message(pm_module):
    root = OSError(24, "Too many open files")
    wrapper = Exception("Something went wrong while authenticating")
    wrapper.__cause__ = root

    assert pm_module.classify_psn_exception(wrapper) == "exhausted"


# Verifies an error the tool has never seen is reported as unknown instead of being mislabeled
def test_unrecognized_errors_are_classified_as_unknown(pm_module):
    assert pm_module.classify_psn_exception(ValueError("brand new failure mode")) == "unknown"


# Verifies the chain walk stops instead of looping forever on a self-referencing exception
def test_chain_walk_is_depth_limited(pm_module):
    looping = RuntimeError("loops back on itself")
    looping.__cause__ = looping

    assert len(list(pm_module.iter_exc_chain(looping, max_depth=4))) == 4


# Verifies the chain walk yields the original exception first
def test_chain_walk_starts_at_the_reported_error(pm_module):
    root = socket.timeout("slow")
    wrapper = chained(root, depth=1)

    assert list(pm_module.iter_exc_chain(wrapper))[0] is wrapper


# Builds a response double carrying only the redirect location header
class FakeRedirect:
    def __init__(self, location=None):
        self.headers = {} if location is None else {"location": location}


# Verifies the probe turns the Terms of Service error code into an instruction the user can act on
def test_auth_probe_reports_terms_of_service_reacceptance(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module.req, "get", lambda *args, **kwargs: FakeRedirect("com.scee.psxandroid.scecompcall://redirect?error=access_denied&error_code=103"))

    hint = pm_module.probe_npsso_auth_error("npsso-test-value")

    assert "Terms of Service" in hint
    assert "https://my.account.sony.com" in hint


# Verifies a Terms of Service rejection is recognized from the description when no error code is sent
def test_auth_probe_recognizes_terms_of_service_from_the_description(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module.req, "get", lambda *args, **kwargs: FakeRedirect("scheme://cb?error=access_denied&error_description=User%20must%20accept%20the%20Terms%20of%20Use"))

    assert "Terms of Service" in pm_module.probe_npsso_auth_error("npsso-test-value")


# Verifies any other rejection is reported verbatim so the cause is visible in the log
def test_auth_probe_reports_other_rejections_verbatim(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module.req, "get", lambda *args, **kwargs: FakeRedirect("scheme://cb?error=invalid_request&error_code=4165"))

    hint = pm_module.probe_npsso_auth_error("npsso-test-value")

    assert "error=invalid_request" in hint
    assert "error_code=4165" in hint


# Verifies a successful redirect produces no hint, so a working token is never reported as broken
def test_auth_probe_stays_silent_when_the_redirect_carries_no_error(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module.req, "get", lambda *args, **kwargs: FakeRedirect("scheme://cb?code=v3.some-authorization-code"))

    assert pm_module.probe_npsso_auth_error("npsso-test-value") is None


# Verifies a probe that cannot reach PSN degrades to no hint instead of raising inside the poll loop
def test_auth_probe_swallows_its_own_failures(pm_module, monkeypatch):
    # Refuses the probe request the way an offline host would
    def explode(*args, **kwargs):
        raise requests.exceptions.ConnectionError("probe host unreachable")

    monkeypatch.setattr(pm_module.req, "get", explode)

    assert pm_module.probe_npsso_auth_error("npsso-test-value") is None


# Verifies the probe never sends the npsso anywhere except the PSN OAuth endpoint it authenticates against
def test_auth_probe_sends_the_token_only_to_sony(pm_module, monkeypatch):
    recorded = {}

    # Captures the outbound probe request
    def capture(url, **kwargs):
        recorded["url"] = url
        recorded["headers"] = kwargs.get("headers", {})
        recorded["allow_redirects"] = kwargs.get("allow_redirects")
        return FakeRedirect()

    monkeypatch.setattr(pm_module.req, "get", capture)
    pm_module.probe_npsso_auth_error("npsso-test-value")

    assert recorded["url"].startswith("https://ca.account.sony.com/")
    assert recorded["headers"]["Cookie"] == "npsso=npsso-test-value"
    assert recorded["allow_redirects"] is False
