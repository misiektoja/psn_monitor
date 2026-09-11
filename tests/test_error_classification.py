"""Tests for the recovery classifier, the advice it renders and the NPSSO auth probe."""

import ast
import inspect
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


# Verifies the descriptor limit is matched as a whole errno, so errno 240 or 241 in a message is not mistaken for it
def test_a_neighbouring_errno_is_not_a_file_descriptor_limit(pm_module):
    assert pm_module.is_too_many_open_files(RuntimeError("[Errno 24] Too many open files")) is True
    assert pm_module.is_too_many_open_files(RuntimeError("[Errno 240] something else")) is False
    assert pm_module.is_too_many_open_files(RuntimeError("[Errno 241] something else")) is False


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
# Every place that reports a problem without the classifier and the reason it cannot use one
CLASSIFIER_EXEMPTIONS = {
    "or higher required": "runs at import on an interpreter too old to load the rest of the file",
    "Couldn't find the pytz library": "raised at import, while a dependency the classifier itself needs is missing",
    "Couldn't find the PSNAWP library": "raised at import, while a dependency the classifier itself needs is missing",
    "Cannot clear the screen contents": "a cosmetic notice with nothing for the operator to recover from",
    "Rebuilt the PSNAWP session after": "reports the recovery action taken, printed under the classified advice",
    "Setup needs a writable dotenv file": "an answer hint inside the question that re-asks, where the next prompt is the recovery",
    "Monitoring failure changed for": "a one-line note on a classified outage that already had its full report",
}

# Words that mark a printed line as a report of something going wrong
TROUBLE_WORDS = re.compile(r"error|cannot|can't|failed|failure|invalid|not valid|missing|not installed|no such|refused|unsupported|needs to be|could not|couldn't|unable to", re.IGNORECASE)


# Returns the literal text one print argument shows, leaving out the parts an f-string fills at runtime
def printed_text(node):
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else ""
    if isinstance(node, ast.JoinedStr):
        return "".join(printed_text(part) for part in node.values)
    if isinstance(node, ast.BinOp):
        return printed_text(node.left) + printed_text(node.right)
    return ""


# Returns every printed line that reads as a problem, paired with the line it sits on
def reported_problems(source):
    found = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}):
            continue
        text = " ".join(printed_text(argument) for argument in node.args)
        if TROUBLE_WORDS.search(text):
            found.append((node.lineno, " ".join(text.split())))
    return found


# A problem reported without a category leaves the reader with a message and no next step
def test_every_reported_problem_goes_through_the_classifier():
    unexplained = [f"line {line}: {text[:120]}" for line, text in reported_problems(SOURCE.read_text(encoding="utf-8")) if not any(marker in text for marker in CLASSIFIER_EXEMPTIONS)]

    assert unexplained == []


# An exemption list that stopped matching anything would quietly cover the whole file
def test_the_classifier_guard_still_inspects_the_source():
    source = SOURCE.read_text(encoding="utf-8")
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}]
    problems = reported_problems(source)

    assert len(inspected) > 200
    assert all(any(marker in text for _, text in problems) for marker in CLASSIFIER_EXEMPTIONS), "an exemption stopped matching a printed line"


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
    assert pm_module.install_command_prefix(method="pip") == ["psn_monitor"]
    assert pm_module.install_command_prefix(method="manual")[-1] == "psn_monitor.py"
    assert pm_module.install_command_prefix(method="manual")[0].startswith("python")
    assert pm_module.render_command(["--generate-config", "psn_monitor.conf"], method="pip") == "psn_monitor --generate-config psn_monitor.conf"


# Verifies an argument that needs quoting is quoted, so the printed command survives a copy and paste
def test_printed_commands_quote_what_the_shell_would_split(pm_module):
    rendered = pm_module.render_command(["--config-file", "/tmp/my configs/psn.conf"], method="pip")

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

    pm_module.print_recovery_advice(outage, tracker=tracker)
    pm_module.print_recovery_advice(outage, tracker=tracker)
    first, repeat = capsys.readouterr().out.rstrip("\n").split("\n* Error:")

    assert "To fix:" in first
    assert "To fix:" not in repeat


# Verifies a different failure prints its own fix, and that a recovery restores the full report
def test_a_changed_or_recovered_failure_prints_the_fix_again(pm_module, capsys):
    tracker = pm_module.RecoveryHintTracker()
    outage = pm_module.classify_recovery_error(Exception("Connection reset by peer"))
    rejected = pm_module.classify_recovery_error(Exception("Your npsso code has expired"))

    pm_module.print_recovery_advice(outage, tracker=tracker)
    pm_module.print_recovery_advice(rejected, tracker=tracker)
    tracker.reset()
    pm_module.print_recovery_advice(outage, tracker=tracker)

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

    assert pm_module.render_command(["--send-test-webhook"], method="pip") == "psn_monitor --send-test-webhook --config-file /etc/psn.conf --env-file /etc/psn.env"
    assert f"then run: {pm_module.render_command(['--send-test-webhook'])}" in pm_module.classify_recovery_error_offline(ValueError("bad"), context="webhook").fix


# Verifies the missing-target fix carries this run's files and leaves the placeholder readable
def test_the_missing_target_command_carries_the_files_and_the_placeholder(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", "/etc/psn.conf")
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "/etc/psn.env")

    fix = pm_module.classify_recovery_error_offline(context="target.missing").fix

    assert "psn_monitor.py <psn_user_id> --config-file /etc/psn.conf --env-file /etc/psn.env" in fix
    assert "'<psn_user_id>'" not in fix


# Verifies a <placeholder> is printed for the reader to replace rather than quoted as a literal value
def test_a_placeholder_argument_is_left_unquoted(pm_module):
    assert pm_module.render_command(["<psn_user_id>", "-n", "<npsso_code>"], include_paths=False, method="pip") == "psn_monitor <psn_user_id> -n <npsso_code>"
    assert pm_module.render_command(["a value"], include_paths=False, method="pip") == "psn_monitor 'a value'"


# Verifies --generate-config keeps the paths out, since it writes the new file at the name in the command
def test_the_generate_config_command_leaves_this_run_out(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", "/etc/psn.conf")
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "/etc/psn.env")

    assert pm_module.render_command(["--generate-config", "psn_monitor.conf"], method="pip", include_paths=False) == "psn_monitor --generate-config psn_monitor.conf"


# Verifies the disabled dotenv search reaches the commands that accept it and stays out of the ones that refuse it
def test_a_disabled_dotenv_search_is_carried_only_where_it_is_accepted(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "none")

    assert pm_module.render_command(["--doctor"], method="pip") == "psn_monitor --doctor --env-file none"
    assert pm_module.render_command(["--set-npsso"], method="pip") == "psn_monitor --set-npsso"
    assert pm_module.render_command(["--setup"], method="pip") == "psn_monitor --setup"


# Verifies the disabled config search reaches the commands that accept it and stays out of the ones that refuse it
def test_a_disabled_config_search_is_carried_only_where_it_is_accepted(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(pm_module, "CONFIG_DISCOVERY_DISABLED", True)
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "")

    assert pm_module.render_command(["--doctor"], method="pip") == "psn_monitor --doctor --config-file none"
    assert pm_module.render_command(["--set-npsso"], method="pip") == "psn_monitor --set-npsso --config-file none"
    assert pm_module.render_command(["--setup"], method="pip") == "psn_monitor --setup"
    assert pm_module.render_command(["--doctor"], method="pip", include_paths=False) == "psn_monitor --doctor"


# Verifies a caller that already names a file is not given a second copy of it
def test_a_path_the_caller_passed_is_not_repeated(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", "/etc/psn.conf")
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "/etc/psn.env")

    rendered = pm_module.render_command(["--doctor", "--config-file", "/tmp/other.conf"], method="pip")

    assert rendered == "psn_monitor --doctor --config-file /tmp/other.conf --env-file /etc/psn.env"


# Verifies added context does not replace the error text the rules read, which used to make every such failure unknown
@pytest.mark.parametrize("message, expected", [("429 rate limit exceeded", "psn.rate_limited"), ("Connection timed out", "network.timeout")])
def test_a_caller_supplied_detail_does_not_hide_the_error(pm_module, message, expected):
    advice = pm_module.classify_recovery_error(Exception(message), detail="Cannot read the PSN profile")

    assert advice.code == expected
    assert "Cannot read the PSN profile" in advice.detail


# The only advice that names no page, and the reason no page covers it
GUIDELESS_ADVICE = {
    "The connectivity endpoint did not answer in time": "no page covers this check and the doctor report already ends with the troubleshooting link",
    "The connectivity endpoint could not be reached": "no page covers this check and the doctor report already ends with the troubleshooting link",
}

# The guide sits in this positional slot for each builder, or inside the fix when the signature carries no slot
GUIDE_SLOT = {"advice": 4, "make_recovery_advice": 5}


# True when this builder attaches a documentation link in any of the three shapes the tool uses
def attaches_a_guide(node, source):
    slot = GUIDE_SLOT.get(getattr(node.func, "id", ""))
    if slot is not None and len(node.args) > slot:
        return True
    if any(keyword.arg in ("guide_url", "guide") for keyword in node.keywords):
        return True
    return "recovery_fix_with_guide" in (ast.get_source_segment(source, node.args[2]) or "")


# Returns every expression assigned to each plain name in the module, so a fix held in a variable can be read
def assigned_expressions(tree):
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
    return assignments


# Returns the text of the summary or fix, resolving one level of plain-name assignment
def resolved_text(node, source, assignments):
    if isinstance(node, ast.Name):
        return " ".join(ast.get_source_segment(source, value) or "" for value in assignments.get(node.id, []))
    return ast.get_source_segment(source, node) or ""


# Returns every advice builder that names no page, paired with the summary it reports
def guideless_advice(source):
    tree = ast.parse(source)
    assignments = assigned_expressions(tree)
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT) or len(node.args) < 3:
            continue
        # A builder that re-wraps an already-classified advice carries whatever guide that advice was given
        if isinstance(node.args[2], ast.Attribute) and node.args[2].attr == "fix":
            continue
        if attaches_a_guide(node, source) or "recovery_fix_with_guide" in resolved_text(node.args[2], source, assignments):
            continue
        found.append((node.lineno, resolved_text(node.args[1], source, assignments)))
    return found


# A failure with no page to read leaves the operator with a one-line fix and nowhere to go next
def test_every_failure_names_a_page():
    source = SOURCE.read_text(encoding="utf-8")
    unexplained = [f"line {line}: {summary[:100]}" for line, summary in guideless_advice(source) if not any(marker in summary for marker in GUIDELESS_ADVICE)]

    assert unexplained == []


# An allowlist that stopped matching anything would quietly cover every failure in the file
def test_the_guide_guard_still_inspects_the_source():
    source = SOURCE.read_text(encoding="utf-8")
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT]
    bare = guideless_advice(source)

    assert len(inspected) > 40
    assert all(any(marker in summary for _, summary in bare) for marker in GUIDELESS_ADVICE), "an allowlisted summary stopped matching a builder"


# One concept carried three names across this family: a renderer taking a built advice, a renderer taking the
# failure itself, and a third pair that classified and printed under a name of its own. Pinned here so a call
# copied from a sibling cannot quietly mean something else
def test_the_recovery_printers_share_one_contract(pm_module):
    advice_first = ("advice", "debug", "retry_note", "with_fix", "label")
    error_first = ("error", "context", "debug", "detail", "retry_note", "with_fix", "label")

    assert tuple(inspect.signature(pm_module.render_recovery_advice).parameters) == advice_first
    assert tuple(inspect.signature(pm_module.render_recovery_error).parameters) == error_first + ("probe_auth",)
    # This tool's own parameters follow the shared ones, so a call written for a sibling still means the same thing
    assert tuple(inspect.signature(pm_module.print_recovery_advice).parameters) == advice_first + ("tracker",)
    assert tuple(inspect.signature(pm_module.print_recovery_error).parameters) == error_first + ("tracker", "probe_auth")


# The advice pair prints what the caller built, so a summary the classifier would never produce survives the trip
def test_the_advice_printer_does_not_reclassify(pm_module, capsys):
    pm_module.DEBUG_MODE = False
    advice = pm_module.make_recovery_advice("network.timeout", "a summary no rule produces", "a fix of its own", True)

    returned = pm_module.print_recovery_advice(advice)

    assert capsys.readouterr().out == "* Error: a summary no rule produces\nTo fix: a fix of its own\n"
    assert returned is advice


# The error pair classifies what the caller hands it, which is the difference between the two front doors
def test_the_error_printer_classifies_what_it_was_given(pm_module, capsys):
    pm_module.DEBUG_MODE = False

    returned = pm_module.print_recovery_error(Exception("Connection reset by peer"), context="runtime")

    assert returned.code != "unknown"
    assert capsys.readouterr().out.startswith(f"* Error: {returned.summary}\n")


# Both front doors reach the same renderer, so the retry note, the label and a suppressed fix behave the same way
def test_both_front_doors_render_the_same_line(pm_module):
    pm_module.DEBUG_MODE = False
    error = Exception("Connection reset by peer")
    advice = pm_module.classify_recovery_error(error, "runtime")

    through_advice = pm_module.render_recovery_advice(advice, retry_note="retrying in 5 minutes", with_fix=False, label="Warning")
    through_error = pm_module.render_recovery_error(error, "runtime", retry_note="retrying in 5 minutes", with_fix=False, label="Warning")

    assert through_advice == through_error
    assert through_advice == f"* Warning: {advice.summary} (retrying in 5 minutes)"


# A detail that only repeats the summary spends a line saying nothing, so the block drops it and keeps a real one
def test_a_detail_repeating_the_summary_is_dropped(pm_module):
    repeated = pm_module.make_recovery_advice("unknown", "the same sentence twice", "a fix", False, "the same sentence twice")
    differing = pm_module.make_recovery_advice("unknown", "the summary", "a fix", False, "the raw cause")

    assert "Technical detail:" not in pm_module.render_recovery_advice(repeated, debug=True)
    assert "Technical detail: the raw cause" in pm_module.render_recovery_advice(differing, debug=True)


# A run that already prints the technical cause cannot be told to re-run for it
def test_the_unrecognized_failure_fix_follows_the_diagnostic_mode(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "DEBUG_MODE", False)
    plain = pm_module.classify_recovery_error(Exception("a wholly unfamiliar failure"), "runtime").fix
    monkeypatch.setattr(pm_module, "DEBUG_MODE", True)
    debugging = pm_module.classify_recovery_error(Exception("a wholly unfamiliar failure"), "runtime").fix

    assert "--debug" in plain
    assert "--debug" not in debugging


# Verifies the printed-command renderer takes the family's two shared parameters before any tool-specific one
def test_the_command_renderer_shares_one_contract(pm_module):
    parameters = list(inspect.signature(pm_module.render_command).parameters.values())
    assert [parameter.name for parameter in parameters[:2]] == ["arguments", "include_paths"]
    assert [parameter.default for parameter in parameters[:2]] == [None, True]
    # A tool-specific extra is keyword-only, so a positional call copied from a sibling cannot bind to it
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters[2:])


# Verifies the renderer with no arguments prints the bare command, which is what the help screen puts before each example
def test_the_renderer_with_no_arguments_prints_the_bare_command(pm_module):
    prefix = pm_module.render_command(include_paths=False)
    assert prefix and not prefix.endswith(" ")
    assert pm_module.render_command(["--doctor"], include_paths=False) == f"{prefix} --doctor"
