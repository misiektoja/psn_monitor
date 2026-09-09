"""Tests for the recovery classifier, the advice it renders and the NPSSO auth probe."""

import ast
import re
import socket
from pathlib import Path

import pytest
import requests

psnawp_exceptions = pytest.importorskip("psnawp_api.core.psnawp_exceptions")

SOURCE = Path(__file__).resolve().parent.parent / "psn_monitor.py"


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
    advice = pm_module.classify_recovery_error(Exception(message))

    assert advice.code == "auth.npsso_invalid"
    assert pm_module.recovery_poll_kind(advice) == "auth"


# Verifies the same rejection during monitoring is a separate code, because a token that worked has since expired
def test_a_rejection_during_monitoring_is_reported_as_an_expired_token(pm_module):
    startup = pm_module.classify_recovery_error(Exception("Your npsso code has expired"), context="startup")
    monitoring = pm_module.classify_recovery_error(Exception("Your npsso code has expired"), context="monitor")

    assert (startup.code, monitoring.code) == ("auth.npsso_invalid", "auth.npsso_expired")
    # Only the running process can be fixed without a restart, so only it is told about SIGHUP
    assert "SIGHUP" in monitoring.fix
    assert "SIGHUP" not in startup.fix


# Verifies the library's own authentication error is recognized wherever it sits in the cause chain
def test_library_authentication_error_is_recognized_through_the_chain(pm_module):
    root = psnawp_exceptions.PSNAWPAuthenticationError("token refused")

    assert pm_module.classify_recovery_error(chained(root)).code == "auth.npsso_invalid"


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
    advice = pm_module.classify_recovery_error(chained(root))

    assert advice.code in {"network.timeout", "network.unavailable"}
    assert pm_module.recovery_poll_kind(advice) == "transient"
    assert advice.retryable is True


@pytest.mark.parametrize("message", [
    "Remote end closed connection without response",
    "Connection reset by peer",
    "Connection aborted",
    "Read timed out",
    "Service temporarily unavailable",
])
# Verifies a transient failure that arrives only as text is still treated as transient
def test_transient_failures_without_a_type_are_recognized_by_message(pm_module, message):
    assert pm_module.recovery_poll_kind(pm_module.classify_recovery_error(Exception(message))) == "transient"


# Verifies an unexpected response shape is classified as malformed so the session is recreated
def test_malformed_response_is_classified_as_malformed(pm_module):
    root = pm_module.PsnMalformedResponse("onlineStatus is empty")

    advice = pm_module.classify_recovery_error(chained(root))

    assert advice.code == "psn.malformed_response"
    assert pm_module.recovery_poll_kind(advice) == "malformed"


@pytest.mark.parametrize("root", [AttributeError("'NoneType' object has no attribute 'get'"), TypeError("string indices must be integers")])
# Verifies the attribute and type errors a changed payload produces are treated as malformed, not unknown
def test_payload_shape_errors_fall_back_to_malformed(pm_module, root):
    assert pm_module.classify_recovery_error(chained(root)).code == "psn.malformed_response"


# Verifies a rate limit is separated from a generic failure, since the fix is to poll less often
def test_rate_limiting_is_reported_with_the_interval_settings(pm_module):
    advice = pm_module.classify_recovery_error(psnawp_exceptions.PSNAWPTooManyRequestsError("429 slow down"))

    assert advice.code == "psn.rate_limited"
    assert "PSN_CHECK_INTERVAL" in advice.fix


# Verifies an unknown PlayStation ID is separated from an auth problem, because only the operator can correct it
def test_an_unknown_playstation_id_is_reported_as_such(pm_module):
    advice = pm_module.classify_recovery_error(psnawp_exceptions.PSNAWPNotFoundError("user not found"))

    assert advice.code == "target.not_found"
    assert advice.retryable is False


# Verifies a profile that hides its activity produces the privacy instructions rather than a generic error
def test_a_hidden_profile_is_reported_with_the_privacy_steps(pm_module):
    advice = pm_module.classify_recovery_error(psnawp_exceptions.PSNAWPForbiddenError("403 forbidden"))

    assert advice.code == "target.not_visible"
    assert "Privacy Settings" in advice.fix


@pytest.mark.parametrize("root", [
    OSError(24, "Too many open files"),
    Exception("OSError(24, 'Too many open files')"),
    Exception("[Errno 24] Too many open files"),
])
# Verifies local file descriptor exhaustion is separated from PSN problems, since only the operator can fix it
def test_file_descriptor_exhaustion_is_classified_as_exhausted(pm_module, root):
    advice = pm_module.classify_recovery_error(chained(root))

    assert advice.code == "resource.exhausted"
    assert pm_module.recovery_poll_kind(advice) == "exhausted"
    assert pm_module.is_too_many_open_files(chained(root)) is True


# Verifies an unrelated OS error is not mistaken for descriptor exhaustion
def test_other_os_errors_are_not_treated_as_exhaustion(pm_module):
    assert pm_module.is_too_many_open_files(OSError(2, "No such file or directory")) is False


# Verifies descriptor exhaustion outranks an auth message, because retrying auth cannot fix a local limit
def test_exhaustion_outranks_an_auth_message(pm_module):
    root = OSError(24, "Too many open files")
    wrapper = Exception("Something went wrong while authenticating")
    wrapper.__cause__ = root

    assert pm_module.classify_recovery_error(wrapper).code == "resource.exhausted"


# Verifies an error the tool has never seen is reported as unknown instead of being mislabeled
def test_unrecognized_errors_are_classified_as_unknown(pm_module):
    assert pm_module.classify_recovery_error(ValueError("brand new failure mode")).code == "unknown"


# Verifies a caller that already knows the category gets it back, without an exception to inspect
@pytest.mark.parametrize("context, code", [
    ("config.missing", "config.missing"),
    ("config.invalid", "config.invalid"),
    ("secret.missing", "secret.missing"),
    ("target.missing", "target.missing"),
    ("smtp.settings", "smtp.invalid"),
    ("file.unreadable", "file.unreadable"),
    ("file.unwritable", "file.unwritable"),
])
def test_a_known_context_selects_its_category_without_an_exception(pm_module, context, code):
    assert pm_module.classify_recovery_error(context=context, detail="something specific went wrong").code == code


# Verifies a caller-supplied detail reaches the summary, so the specific problem is not replaced by a generic one
def test_the_caller_detail_is_what_the_operator_reads(pm_module):
    advice = pm_module.classify_recovery_error(context="config.missing", detail="Config file 'missing.conf' does not exist")

    assert "missing.conf" in advice.summary


# Verifies descriptor exhaustion still wins over a file context, since no file permission change would help
def test_exhaustion_outranks_a_file_context(pm_module):
    assert pm_module.classify_recovery_error(OSError(24, "Too many open files"), context="file.unwritable").code == "resource.exhausted"


# Verifies SMTP login rejection is separated from an unreachable server, because the two fixes differ
def test_smtp_failures_are_split_by_cause(pm_module):
    import smtplib

    rejected = pm_module.classify_recovery_error(smtplib.SMTPAuthenticationError(535, b"auth failed"), context="smtp")
    unreachable = pm_module.classify_recovery_error(smtplib.SMTPServerDisconnected("connection lost"), context="smtp")

    assert (rejected.code, unreachable.code) == ("smtp.authentication", "smtp.connection")
    assert rejected.retryable is False and unreachable.retryable is True


# Verifies advice already attached to an exception is used as it is, instead of being classified a second time
def test_attached_advice_survives_the_exception_boundary(pm_module):
    advice = pm_module.make_recovery_advice("target.not_found", "summary", "fix", False)

    assert pm_module.classify_recovery_error(pm_module.RecoveryError(advice, ValueError("root cause"))).code == "target.not_found"


# Verifies a code outside the taxonomy is refused, so the set of categories stays closed
def test_an_unsupported_code_is_refused(pm_module):
    with pytest.raises(ValueError):
        pm_module.make_recovery_advice("psn.brand_new_thing", "summary", "fix", True)


# Returns every recovery code named in the first argument of each make_recovery_advice call
def produced_recovery_codes(source):
    codes = set()
    for start in (match.end() for match in re.finditer(r"make_recovery_advice\(", source)):
        depth, index = 1, start
        while depth and index < len(source):
            depth += {"(": 1, ")": -1}.get(source[index], 0)
            if depth == 1 and source[index] == ",":
                break
            index += 1
        codes.update(re.findall(r'"([^"]+)"', source[start:index]))
    return codes


# Verifies every declared category is actually produced by the tool, so the taxonomy carries no dead entries
def test_every_declared_category_is_produced_somewhere(pm_module):
    assert produced_recovery_codes(SOURCE.read_text(encoding="utf-8")) == set(pm_module.RECOVERY_CODES)


# Verifies the retry policy covers every category the loop retries, leaving only the one it refuses to retry
def test_every_retried_category_maps_to_a_policy(pm_module):
    kinds = {pm_module.recovery_poll_kind(pm_module.RecoveryAdvice(code, "s", "f", True)) for code in pm_module.RECOVERY_CODES}

    assert kinds - set(pm_module.RECOVERY_POLL_POLICY) == {"exhausted"}


# Every place that reports a problem without the classifier, and the reason it cannot use one
CLASSIFIER_EXEMPTIONS = {
    "or higher required": "runs at import on an interpreter too old to load the rest of the file",
    "Couldn't find the pytz library": "raised at import, while a dependency the classifier itself needs is missing",
    "Couldn't find the PSNAWP library": "raised at import, while a dependency the classifier itself needs is missing",
    "sanitize_error_text(message)": "the debug and verbose printers, whose content the redactor guard covers",
    "Cannot clear the screen contents": "a cosmetic notice with nothing for the operator to recover from",
    "Rebuilt the PSNAWP session after": "reports the recovery action taken, printed under the classified advice",
}

# Words that mark a printed line as a report of something going wrong
TROUBLE_WORDS = re.compile(r"error|cannot|can't|failed|failure|invalid|not valid|missing|not installed|no such|refused|unsupported|needs to be", re.IGNORECASE)


# Verifies every reported problem carries a recovery category, so the operator is never left without a fix
def test_every_reported_problem_goes_through_the_classifier():
    source = SOURCE.read_text(encoding="utf-8")
    unexplained = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}):
            continue
        segment = ast.get_source_segment(source, node) or ""
        if TROUBLE_WORDS.search(segment) and not any(marker in segment for marker in CLASSIFIER_EXEMPTIONS):
            unexplained.append(f"line {node.lineno}: {' '.join(segment.split())[:120]}")

    assert unexplained == []


# Verifies the guard above still has something to find, so an exemption cannot quietly cover everything
def test_the_classifier_guard_still_inspects_the_source():
    source = SOURCE.read_text(encoding="utf-8")
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}]

    assert len(inspected) > 100
    assert all(marker in source for marker in CLASSIFIER_EXEMPTIONS)


# Verifies the install is detected from how the tool was started, since the commands to print differ
@pytest.mark.parametrize("argv_zero, method", [
    ("/usr/local/bin/psn_monitor", "pip"),
    ("psn_monitor", "pip"),
    ("./psn_monitor.py", "manual"),
    ("/home/someone/psn_monitor.py", "manual"),
])
def test_the_install_method_is_detected_from_the_entry_point(pm_module, monkeypatch, argv_zero, method):
    monkeypatch.setattr(pm_module.sys, "argv", [argv_zero])

    assert pm_module.detect_install_method() == method


# Verifies a printed command matches the install, so a downloaded script is never told to run a console script
def test_printed_commands_match_the_install(pm_module):
    assert pm_module.tool_command_prefix(method="pip") == "psn_monitor"
    assert pm_module.tool_command_prefix(method="manual").endswith("psn_monitor.py")
    assert pm_module.tool_command_prefix(method="manual").startswith("python")
    assert pm_module.tool_command("--generate-config", "psn_monitor.conf", method="pip") == "psn_monitor --generate-config psn_monitor.conf"


# Verifies an argument that needs quoting is quoted, so the printed command survives a copy and paste
def test_printed_commands_quote_what_the_shell_would_split(pm_module):
    rendered = pm_module.tool_command("--config-file", "/tmp/my configs/psn.conf", method="pip")

    assert "my configs" in rendered
    assert rendered != "psn_monitor --config-file /tmp/my configs/psn.conf"


# Verifies the fix text is built for the detected install rather than assuming one
def test_the_fix_text_follows_the_detected_install(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module.sys, "argv", ["/usr/local/bin/psn_monitor"])
    installed = pm_module.classify_recovery_error(context="secret.missing").fix
    monkeypatch.setattr(pm_module.sys, "argv", ["./psn_monitor.py"])
    downloaded = pm_module.classify_recovery_error(context="secret.missing").fix

    assert "psn_monitor <psn_user_id>" in installed
    assert "psn_monitor.py <psn_user_id>" in downloaded


# Verifies the technical detail is held back until debug mode asks for it
def test_the_technical_detail_is_debug_only(pm_module):
    advice = pm_module.classify_recovery_error(ValueError("raw library text"), detail="raw library text")

    assert "Technical detail" not in pm_module.render_recovery_advice(advice, debug=False)
    assert "Technical detail: raw library text" in pm_module.render_recovery_advice(advice, debug=True)


# Verifies the fix paragraph is printed once per category, so a long outage does not repeat it every retry
def test_the_fix_paragraph_is_not_repeated_while_the_same_failure_persists(pm_module, capsys):
    tracker = pm_module.RecoveryHintTracker()
    outage = pm_module.classify_recovery_error(Exception("Connection reset by peer"))

    pm_module.print_recovery_advice(outage, tracker)
    pm_module.print_recovery_advice(outage, tracker)
    first, repeat = capsys.readouterr().out.rstrip("\n").split("\n* Error:")

    assert "To fix:" in first
    assert "To fix:" not in repeat


# Verifies a different failure prints its own fix, and that a recovery restores the full report
def test_a_changed_or_recovered_failure_prints_the_fix_again(pm_module, capsys):
    tracker = pm_module.RecoveryHintTracker()
    outage = pm_module.classify_recovery_error(Exception("Connection reset by peer"))
    rejected = pm_module.classify_recovery_error(Exception("Your npsso code has expired"))

    pm_module.print_recovery_advice(outage, tracker)
    pm_module.print_recovery_advice(rejected, tracker)
    tracker.reset()
    pm_module.print_recovery_advice(outage, tracker)

    assert capsys.readouterr().out.count("To fix:") == 3


# Verifies a non-fatal problem is labelled a warning, since the tool carries on without the missing library
def test_a_survivable_problem_is_reported_as_a_warning(pm_module):
    advice = pm_module.missing_dependency_advice("tzlocal", "The local timezone could not be detected")

    assert advice.code == "dependency.missing"
    assert pm_module.render_recovery_advice(advice, label="Warning").startswith("* Warning: ")


# Verifies a secret cannot reach the screen through advice, whichever field it was placed in
def test_advice_redacts_every_field_it_carries(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "aVeryLongNpssoValue1234567890")
    advice = pm_module.make_recovery_advice("unknown", "failed with aVeryLongNpssoValue1234567890", "retry with aVeryLongNpssoValue1234567890", True, "npsso=aVeryLongNpssoValue1234567890")

    assert "aVeryLongNpssoValue1234567890" not in pm_module.render_recovery_advice(advice, debug=True)


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


# Builds a response double shaped like the redirect the PSN OAuth endpoint returns
class FakeRedirect:
    def __init__(self, location=None, status_code=302):
        self.status_code = status_code
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


# Verifies a printed command carries the files this run was given, so the retest reads the settings that failed
def test_printed_commands_carry_the_files_this_run_was_given(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", "/etc/psn.conf")
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "/etc/psn.env")

    assert pm_module.tool_command("--send-test-webhook", method="pip") == "psn_monitor --send-test-webhook --config-file /etc/psn.conf --env-file /etc/psn.env"
    assert f"then run: {pm_module.tool_command('--send-test-webhook')}" in pm_module.classify_recovery_error_offline(ValueError("bad"), context="webhook").fix


# Verifies the missing-target fix carries this run's files and leaves the placeholder readable
def test_the_missing_target_command_carries_the_files_and_the_placeholder(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", "/etc/psn.conf")
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "/etc/psn.env")

    fix = pm_module.classify_recovery_error_offline(context="target.missing").fix

    assert "psn_monitor.py <psn_user_id> --config-file /etc/psn.conf --env-file /etc/psn.env" in fix
    assert "'<psn_user_id>'" not in fix


# Verifies a <placeholder> is printed for the reader to replace rather than quoted as a literal value
def test_a_placeholder_argument_is_left_unquoted(pm_module):
    assert pm_module.render_command(["<psn_user_id>", "-n", "<npsso_code>"]) == "<psn_user_id> -n <npsso_code>"
    assert pm_module.render_command(["a value"]) == "'a value'"


# Verifies --generate-config keeps the paths out, since it writes the new file at the name in the command
def test_the_generate_config_command_leaves_this_run_out(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", "/etc/psn.conf")
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "/etc/psn.env")

    assert pm_module.tool_command("--generate-config", "psn_monitor.conf", method="pip", include_paths=False) == "psn_monitor --generate-config psn_monitor.conf"


# Verifies the disabled dotenv search reaches the commands that accept it and stays out of the ones that refuse it
def test_a_disabled_dotenv_search_is_carried_only_where_it_is_accepted(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "none")

    assert pm_module.tool_command("--doctor", method="pip") == "psn_monitor --doctor --env-file none"
    assert pm_module.tool_command("--set-npsso", method="pip") == "psn_monitor --set-npsso"
    assert pm_module.tool_command("--setup", method="pip") == "psn_monitor --setup"


# Verifies a caller that already names a file is not given a second copy of it
def test_a_path_the_caller_passed_is_not_repeated(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", "/etc/psn.conf")
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "/etc/psn.env")

    rendered = pm_module.tool_command("--doctor", "--config-file", "/tmp/other.conf", method="pip")

    assert rendered == "psn_monitor --doctor --config-file /tmp/other.conf --env-file /etc/psn.env"
