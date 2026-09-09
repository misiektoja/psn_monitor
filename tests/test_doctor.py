"""Tests for --doctor: the report contract, every section it prints and the exit code it returns.

The output contract lives in the seam between the functions, not inside any one of
them, so the contract tests drive the whole run and read the transcript a user sees.
"""

import re
import smtplib

import pytest

from conftest import presence_payload


# Fails the test if Doctor tries to sign in on a path that must never reach the network
def _unreachable_smtp(*args, **kwargs):
    raise AssertionError("Doctor must not open an SMTP connection when the sign-in cannot be attempted")


# Lets the passive sign-in succeed without contacting a server, for the tests that need a ready email channel
@pytest.fixture
def smtp_sign_in_ok(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "smtp_sign_in", lambda password, timeout=15: pm_module.SMTP_USER)


USER_ID = "misiektoja"
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"

# The four shared markers. A fifth is the drift these tests exist to catch
MARKERS = ("PASS", "WARN", "FAIL", "SKIP")

MARKER_RE = re.compile(r"^\[([A-Z -]+)\]")


# Stands in for an interactive terminal, collecting print output and progress writes in one buffer
class FakeTerminal:
    def __init__(self, interactive=True):
        self.interactive = interactive
        self.chunks = []

    def isatty(self):
        return self.interactive

    def write(self, text):
        self.chunks.append(text)
        return len(text)

    def flush(self):
        pass

    @property
    def text(self):
        return "".join(self.chunks)


# Collapses carriage-return overwrites the way a terminal does, so cleared progress does not read as content
def as_displayed(raw):
    return "\n".join(line.split("\r")[-1].rstrip() for line in raw.split("\n"))


@pytest.fixture
# Runs the doctor against a fake interactive terminal and returns what the user would see
def doctor_run(pm_module, monkeypatch):
    def run(interactive=True, **kwargs):
        terminal = FakeTerminal(interactive)
        monkeypatch.setattr(pm_module.sys, "stdout", terminal)
        monkeypatch.setattr(pm_module.sys, "stdin", terminal)
        code = pm_module.run_doctor(**kwargs)
        return code, terminal.text
    return run


@pytest.fixture(autouse=True)
# Keeps every run offline and away from any config or dotenv file the developer happens to have
def offline_doctor(monkeypatch, pm_module, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pm_module, "probe_npsso_auth_error", lambda npsso: None)
    monkeypatch.setattr(pm_module, "DEFAULT_CONFIG_FILENAME", "psn_monitor_test_only.conf")
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(pm_module, "check_internet", lambda *args, **kwargs: True)


# Returns every check the doctor produced for one section
def checks_in(report, section):
    return [check for check in report.checks if check.section == section]


# Returns the first check whose label starts with the given text
def check_labelled(report, prefix):
    return next(check for check in report.checks if check.label.startswith(prefix))


# Verifies the preflight notice, the progress line and the heading arrive in the documented order
def test_the_report_is_printed_in_the_documented_order(pm_module, psn_session, doctor_run):
    psn_session([presence_payload(status="online")])

    _, raw = doctor_run(psn_user_id=USER_ID)

    notice = raw.index("Running preflight checks.")
    progress = raw.index("* Checking environment ...")
    # The heading is written straight after the progress line is erased, so there is no newline before it
    heading = raw.index("Doctor\nDetected install method:")
    assert notice < progress < heading


# Verifies the preflight notice names both channels the delivery tests can offer, so neither is a surprise
def test_the_preflight_notice_names_both_delivery_channels(pm_module, psn_session, doctor_run):
    psn_session([presence_payload(status="online")])

    _, raw = doctor_run(psn_user_id=USER_ID)

    assert "Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval." in raw


# Verifies the transient progress line leaves nothing behind in the report the user reads
def test_the_progress_line_is_cleared_before_the_report(pm_module, psn_session, doctor_run):
    psn_session([presence_payload(status="online")])

    _, raw = doctor_run(psn_user_id=USER_ID)

    assert "* Checking" not in as_displayed(raw)


# Verifies no progress is written at all when the output is redirected, where it could not be erased
def test_no_progress_is_written_when_the_output_is_not_a_terminal(pm_module, psn_session, doctor_run):
    psn_session([presence_payload(status="online")])

    _, raw = doctor_run(interactive=False, psn_user_id=USER_ID)

    assert "* Checking" not in raw


# Verifies the report never doubles a blank line, which is the drift the shared contract exists to stop
def test_the_report_never_prints_two_blank_lines_in_a_row(pm_module, psn_session, doctor_run):
    psn_session([presence_payload(status="online")])

    _, raw = doctor_run(psn_user_id=USER_ID)

    assert "\n\n\n" not in as_displayed(raw)


# Verifies only the four shared markers appear, since a fifth reads as a different program in a sibling tool
def test_only_the_four_shared_markers_are_used(pm_module, psn_session, doctor_run):
    psn_session([presence_payload(status="online")])

    _, raw = doctor_run(psn_user_id=USER_ID)
    found = {match.group(1) for match in (MARKER_RE.match(line) for line in as_displayed(raw).split("\n")) if match}

    assert found and found <= set(MARKERS)


# Verifies a marker outside the shared four cannot be created at all
def test_an_unsupported_marker_is_refused(pm_module):
    with pytest.raises(ValueError):
        pm_module.make_doctor_check("Environment", "INFO", "something neither good nor bad")


# Verifies the sections appear in their fixed order, so two runs are read the same way
def test_sections_appear_in_the_fixed_order(pm_module, psn_session, doctor_run):
    psn_session([presence_payload(status="online")])

    _, raw = doctor_run(psn_user_id=USER_ID)
    printed = [line for line in as_displayed(raw).split("\n") if line in pm_module.DOCTOR_SECTIONS]

    assert printed == [section for section in pm_module.DOCTOR_SECTIONS if section in printed]
    assert len(printed) == len(set(printed))


# Verifies a fix line is offered on the rows that need one and never on a row that passed
def test_only_the_rows_that_are_not_a_pass_carry_a_fix(pm_module, psn_session, doctor_run, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "")
    psn_session([presence_payload(status="online")])

    _, raw = doctor_run(psn_user_id=USER_ID)
    lines = as_displayed(raw).split("\n")
    for index, line in enumerate(lines):
        if line.startswith("To fix:"):
            preceding = next(item for item in reversed(lines[:index]) if MARKER_RE.match(item))
            assert not preceding.startswith("[PASS]")


# Verifies the run ends with one summary sentence and the guide link, in that order
def test_the_report_ends_with_one_summary_sentence_and_the_guide(pm_module, psn_session, doctor_run):
    psn_session([presence_payload(status="online")])

    _, raw = doctor_run(psn_user_id=USER_ID)
    tail = as_displayed(raw).rstrip("\n").split("\n")[-4:]

    assert tail[0] == "Summary"
    assert tail[1].startswith("  ") and tail[1].endswith(("!", "."))
    assert tail[2] == ""
    assert tail[3] == f"Guide: {pm_module.DOCTOR_GUIDE_URL}"


# Verifies the delivery tests are offered after the check rows but before the summary that counts them
def test_delivery_tests_are_offered_before_the_summary(pm_module, psn_session, monkeypatch, doctor_run, sent_emails, smtp_sign_in_ok):
    monkeypatch.setattr(pm_module, "GAME_CHANGE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "ask_yes_no", lambda question, default=False: False)
    psn_session([presence_payload(status="online")])

    _, raw = doctor_run(psn_user_id=USER_ID)
    displayed = as_displayed(raw)

    assert displayed.index("Notifications") < displayed.index("Optional delivery tests") < displayed.index("Summary")
    assert displayed.index("Summary") < displayed.index(f"Guide: {pm_module.DOCTOR_GUIDE_URL}")


# Verifies a failed delivery test reaches the summary, so the last sentence cannot contradict the exit code
def test_a_failed_delivery_test_reaches_the_summary(pm_module, psn_session, monkeypatch, doctor_run):
    monkeypatch.setattr(pm_module, "GAME_CHANGE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "ask_yes_no", lambda question, default=False: True)
    monkeypatch.setattr(pm_module, "send_email", lambda *args, **kwargs: 1)
    psn_session([presence_payload(status="online")])

    code, raw = doctor_run(psn_user_id=USER_ID)

    assert code == 1
    assert "1 check(s) failed" in as_displayed(raw)
    assert "All checks passed" not in as_displayed(raw)


@pytest.mark.parametrize("failures, warnings, sentence", [
    (0, 0, "  All checks passed. You are good to go!"),
    (0, 2, "  All critical checks passed with 2 warning(s). Review the warnings above."),
    (1, 2, "  1 check(s) failed, 2 warning(s). Fix the failures above before relying on the tool."),
])
# Verifies each outcome gets its own sentence, since a bare count leaves the reader to decide what it means
def test_the_summary_says_what_the_counts_mean(pm_module, failures, warnings, sentence):
    checks = [pm_module.make_doctor_check("Environment", "FAIL", "f") for _ in range(failures)]
    checks += [pm_module.make_doctor_check("Environment", "WARN", "w") for _ in range(warnings)]

    assert sentence in pm_module.render_doctor_summary(checks)


# Verifies the doctor leaves the working directory exactly as it found it
def test_the_doctor_writes_no_files(pm_module, psn_session, doctor_run, monkeypatch, tmp_path):
    monkeypatch.setattr(pm_module, "DISABLE_LOGGING", False)
    monkeypatch.setattr(pm_module, "PSN_LOGFILE", "psn_monitor")
    monkeypatch.setattr(pm_module, "CSV_FILE", str(tmp_path / "history.csv"))
    psn_session([presence_payload(status="online")])
    before = sorted(tmp_path.iterdir())

    doctor_run(psn_user_id=USER_ID)

    assert sorted(tmp_path.iterdir()) == before


# Verifies an interpreter below the minimum fails against the same constant the startup gate uses
def test_an_unsupported_python_version_fails_against_the_shared_minimum(pm_module):
    too_old = (pm_module.MINIMUM_PYTHON_VERSION[0], pm_module.MINIMUM_PYTHON_VERSION[1] - 1, 0)

    check = pm_module.doctor_check_environment(version_info=too_old)[0]

    assert check.status == "FAIL"
    assert pm_module.MINIMUM_PYTHON_VERSION_TEXT in check.advice.fix


# Verifies the running interpreter passes, so the check is not reporting the version without judging it
def test_the_running_python_version_passes(pm_module):
    assert pm_module.doctor_check_environment()[0].status == "PASS"


# Verifies a dependency the tool cannot start without is a failure, not a warning
def test_a_missing_required_dependency_fails(pm_module):
    checks = pm_module.doctor_check_environment(spec_finder=lambda name: None if name == "pytz" else object())

    missing = next(check for check in checks if "pytz" in check.label)
    assert missing.status == "FAIL"
    assert "-m pip install pytz" in missing.advice.fix


# Verifies a dependency the tool degrades around is a warning that names what stops working
def test_a_missing_optional_dependency_warns_and_says_what_breaks(pm_module):
    checks = pm_module.doctor_check_environment(spec_finder=lambda name: None if name == "wcwidth" else object())

    missing = next(check for check in checks if "wcwidth" in check.label)
    assert missing.status == "WARN"
    assert "Screen truncation is disabled" in missing.detail
    assert "Monitoring is unaffected" in missing.detail
    assert "-m pip install wcwidth" in missing.advice.fix


# Verifies a warning about a library that cannot affect this machine is not shown at all
@pytest.mark.parametrize("system, reported", [("Windows", True), ("Linux", False), ("Darwin", False)])
def test_a_platform_specific_dependency_is_only_reported_where_it_applies(pm_module, monkeypatch, system, reported):
    monkeypatch.setattr(pm_module.platform, "system", lambda: system)

    checks = pm_module.doctor_check_environment(spec_finder=lambda name: None)

    assert any("colorama" in check.label for check in checks) is reported


# Verifies the Windows colour library is reported there, so broken colours on that platform have a diagnostic
def test_missing_colorama_is_reported_on_windows(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module.platform, "system", lambda: "Windows")

    checks = pm_module.doctor_check_environment(spec_finder=lambda name: None if name == "colorama" else object())

    missing = next(check for check in checks if "colorama" in check.label)
    assert missing.status == "WARN"
    assert "older Windows Command Prompt" in missing.detail
    assert "-m pip install colorama" in missing.advice.fix


# Verifies the install method is stated under the heading as context, using the raw key support reports use
def test_the_install_method_is_stated_under_the_heading(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module.sys, "argv", ["/usr/local/bin/psn_monitor"])

    rendered = pm_module.render_doctor_sections(pm_module.DoctorReport()).split("\n")

    assert rendered[:2] == ["Doctor", "Detected install method: pip"]
    # It cannot fail, so it never takes a result row that no marker describes
    assert not any(line.startswith("[") and "Install method" in line for line in rendered)


# Verifies the configuration and dotenv files in use are named, since that is what a stale setting looks like
def test_the_configuration_and_dotenv_files_in_use_are_named(pm_module):
    checks = pm_module.doctor_check_configuration(config_path="/etc/psn.conf", env_path="/etc/psn.env")

    assert check_labelled_detail(checks, "Configuration file loaded") == "Path: /etc/psn.conf"
    assert check_labelled_detail(checks, "Dotenv file loaded") == "Path: /etc/psn.env"


# Returns the detail of the first check with the given label
def check_labelled_detail(checks, label):
    return next(check.detail for check in checks if check.label == label)


# Verifies a deliberately bare setup is reported as working rather than as something missing
def test_no_configuration_file_is_a_working_setup(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "")
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "")

    reported = [(check.label, check.status) for check in pm_module.doctor_check_configuration() if check.label.startswith("No ")]

    assert reported == [("No configuration file selected", "PASS"), ("No dotenv file selected", "PASS"), ("No secrets loaded", "PASS")]


# Verifies each secret is reported by name with the source it was resolved from, and never by value
def test_secrets_are_reported_by_name_and_source(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "aVeryLongNpssoValue1234567890")
    monkeypatch.setitem(pm_module.SECRET_SOURCES, "PSN_NPSSO", "dotenv file")
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "aVeryLongSmtpPassword123")
    monkeypatch.setitem(pm_module.SECRET_SOURCES, "SMTP_PASSWORD", "environment")

    rendered = "\n".join(f"{check.label} {check.detail}" for check in pm_module.doctor_secret_checks())

    assert "Secrets loaded from the dotenv file PSN_NPSSO" in rendered
    assert "Secrets loaded from the environment SMTP_PASSWORD" in rendered
    assert "aVeryLongNpssoValue1234567890" not in rendered
    assert "aVeryLongSmtpPassword123" not in rendered


# Verifies a run with no secrets says so rather than printing nothing at all
def test_a_run_with_no_secrets_says_so(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "")
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "")

    assert pm_module.doctor_secret_checks()[0].label == "No secrets loaded"


# Verifies a polling interval low enough to be rate limited is warned about before it costs a run
def test_a_rate_limiting_interval_is_warned_about(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_ACTIVE_CHECK_INTERVAL", 5)

    check = next(item for item in pm_module.doctor_check_configuration() if item.label.startswith("Check intervals"))

    assert check.status == "WARN"
    assert "PSN_ACTIVE_CHECK_INTERVAL" in check.advice.fix


# Verifies a file the tool would write but cannot is a failure the report names with its path
def test_an_unwritable_csv_path_fails_with_its_path(pm_module, monkeypatch, tmp_path):
    monkeypatch.setattr(pm_module, "CSV_FILE", str(tmp_path / "missing-dir" / "history.csv"))

    check = next(item for item in pm_module.doctor_check_configuration() if "CSV" in item.label)

    assert check.status == "FAIL"
    assert "history.csv" in check.label


# Verifies a missing NPSSO is reported as the credential problem it is, not as a rejected login
def test_a_missing_npsso_is_reported_before_any_call(pm_module, psn_session, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "")
    psn_session([presence_payload(status="online")])
    report = pm_module.DoctorReport()

    checks = pm_module.doctor_check_authentication(report)

    assert (checks[0].status, checks[0].advice.code) == ("FAIL", "secret.missing")
    assert psn_session.instances == []


# Verifies a rejected NPSSO is reported with the fix for a rejected NPSSO
def test_a_rejected_npsso_is_reported_with_its_fix(pm_module, monkeypatch):
    # Refuses to build a session the way an expired token does
    def refuse(npsso):
        raise RuntimeError("Your npsso code has expired")

    monkeypatch.setattr(pm_module, "PSNAWP", refuse)

    check = pm_module.doctor_check_authentication(pm_module.DoctorReport())[0]

    assert (check.status, check.advice.code) == ("FAIL", "auth.npsso_invalid")
    assert "Generate a fresh NPSSO code" in check.advice.fix


# Verifies a working NPSSO names the account it signed in as, which is how a wrong token is spotted
def test_a_working_npsso_names_the_signed_in_account(pm_module, psn_session):
    psn_session([presence_payload(status="online")])
    report = pm_module.DoctorReport()

    check = pm_module.doctor_check_authentication(report)[0]

    assert check.status == "PASS"
    assert "signed-in-account" in check.detail
    assert report.psnawp is not None


# Verifies the profile is looked up on the session authentication already built, not on a second one
def test_the_target_reuses_the_authenticated_session(pm_module, psn_session, doctor_run):
    psn_session([presence_payload(status="online")])

    doctor_run(psn_user_id=USER_ID)

    assert len(psn_session.instances) == 1


# Verifies the target section is left out when authentication failed, so one problem is reported once
def test_the_target_section_is_omitted_when_authentication_failed(pm_module, monkeypatch, doctor_run):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "")

    _, raw = doctor_run(psn_user_id=USER_ID, interactive=False)

    assert "\nTarget\n" not in as_displayed(raw)


# Verifies a missing PlayStation ID is its own failure, since nothing can be monitored without one
def test_a_missing_playstation_id_fails_the_target(pm_module, psn_session):
    psn_session([presence_payload(status="online")])
    report = pm_module.DoctorReport()
    pm_module.doctor_check_authentication(report)

    checks = pm_module.doctor_check_target(report, None)

    assert (checks[0].status, checks[0].advice.code) == ("FAIL", "target.missing")


# Verifies a profile that hides its activity is reported with the privacy steps, not as a broken token
def test_a_hidden_profile_is_reported_with_the_privacy_steps(pm_module, psn_session):
    psnawp_exceptions = pytest.importorskip("psnawp_api.core.psnawp_exceptions")
    psn_session([psnawp_exceptions.PSNAWPForbiddenError("403 forbidden")])
    report = pm_module.DoctorReport()
    pm_module.doctor_check_authentication(report)

    checks = pm_module.doctor_check_target(report, USER_ID)

    assert checks[-1].advice.code == "target.not_visible"


# Verifies a reachable profile reports the status the tool actually read back
def test_a_reachable_profile_reports_its_current_status(pm_module, psn_session):
    psn_session([presence_payload(status="online")])
    report = pm_module.DoctorReport()
    pm_module.doctor_check_authentication(report)

    checks = pm_module.doctor_check_target(report, USER_ID)

    assert [check.status for check in checks] == ["PASS", "PASS"]
    assert "Current status: online" in checks[-1].detail


# Verifies a fresh install is not warned at for the error alert that ships on with nothing to send it with
def test_a_fresh_install_reports_email_as_disabled(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "SMTP_HOST", "your_smtp_server_ssl")
    report = pm_module.DoctorReport()

    check = pm_module.doctor_check_notifications(report)[0]

    assert (check.status, check.label) == ("PASS", "Email alerts are disabled")
    assert check.detail == "No SMTP connection was attempted and no email was sent"
    assert report.email_ready is False


# Verifies alerts that were deliberately turned on but cannot be delivered are a warning, not a pass
def test_enabled_alerts_with_broken_settings_warn(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "ACTIVE_INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "SMTP_HOST", "not a hostname")
    report = pm_module.DoctorReport()

    check = pm_module.doctor_check_notifications(report)[0]

    assert check.status == "WARN"
    assert report.email_ready is False


# Verifies a usable channel reports the sign-in, the alerts it would send and that nothing was sent
def test_a_usable_email_channel_reports_the_sign_in_and_the_alerts(pm_module, monkeypatch, smtp_sign_in_ok):
    monkeypatch.setattr(pm_module, "GAME_CHANGE_NOTIFICATION", True)
    report = pm_module.DoctorReport()

    check = pm_module.doctor_check_notifications(report)[0]

    assert (check.status, check.label) == ("PASS", pm_module.SMTP_READY_CHECK_LABEL)
    assert check.detail == "Alerts: game changes. No email was sent during this passive check"
    assert report.email_ready is True


# Verifies the passive check signs in rather than trusting the settings, since a rejected password must not pass
def test_the_email_check_signs_in_before_reporting_ready(pm_module, monkeypatch):
    attempts = []
    monkeypatch.setattr(pm_module, "GAME_CHANGE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "smtp_sign_in", lambda password, timeout=15: attempts.append(timeout) or pm_module.SMTP_USER)
    report = pm_module.DoctorReport()

    pm_module.doctor_check_notifications(report)

    assert attempts == [pm_module.DOCTOR_SMTP_TIMEOUT]


# Verifies a rejected sign-in fails the row and leaves the channel out of the delivery tests
def test_a_rejected_sign_in_fails_the_email_row(pm_module, monkeypatch):
    advice = pm_module.classify_recovery_error(smtplib.SMTPAuthenticationError(535, b"denied"), context="smtp", detail="Signing in failed")

    # Refuses the sign-in the way a wrong app password would
    def reject(password, timeout=15):
        raise pm_module.RecoveryError(advice)

    monkeypatch.setattr(pm_module, "GAME_CHANGE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "smtp_sign_in", reject)
    report = pm_module.DoctorReport()

    check = pm_module.doctor_check_notifications(report)[0]

    assert (check.status, check.advice.code) == ("FAIL", "smtp.authentication")
    assert report.email_ready is False


# Verifies an empty password is reported before any connection is attempted
def test_missing_smtp_credentials_warn_without_connecting(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "GAME_CHANGE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "")
    monkeypatch.setattr(pm_module, "smtp_sign_in", _unreachable_smtp)
    report = pm_module.DoctorReport()

    check = pm_module.doctor_check_notifications(report)[0]

    assert (check.status, check.label) == ("WARN", pm_module.EMAIL_UNUSABLE_CHECK_LABEL)
    assert check.detail == "SMTP_USER or SMTP_PASSWORD is empty or still set to its placeholder"
    assert check.advice is not None
    assert "Set SMTP_USER and SMTP_PASSWORD or turn the email alerts off" in check.advice.fix
    assert pm_module.SMTP_GUIDE_URL in check.advice.fix
    assert report.email_ready is False


# Verifies a fresh install is not warned at for the webhook error alert that ships on with nowhere to send it
def test_a_fresh_install_reports_webhooks_as_disabled(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_ERROR_NOTIFICATION", True)
    report = pm_module.DoctorReport()

    check = pm_module.doctor_check_webhook_notifications(report)[0]

    assert (check.status, check.label) == ("PASS", "Webhook alerts are disabled")
    # The label says everything, so the row carries no detail that only repeats it
    assert check.detail == ""
    assert report.webhook_ready is False


# Verifies alerts selected while the channel is off are a warning, since nothing would ever be delivered
def test_selected_alerts_with_the_channel_off_warn(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_GAME_CHANGE_NOTIFICATION", True)
    report = pm_module.DoctorReport()

    check = pm_module.doctor_check_webhook_notifications(report)[0]

    assert check.status == "WARN"
    assert check.advice.code == "webhook.invalid"
    assert report.webhook_ready is False


# Verifies an enabled channel with no alert selected is a warning rather than a pass
def test_an_enabled_channel_with_no_alerts_warns(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", WEBHOOK_URL)
    report = pm_module.DoctorReport()

    check = pm_module.doctor_check_webhook_notifications(report)[0]

    assert check.status == "WARN"
    assert report.webhook_ready is False


# Verifies each unusable webhook setting is reported as a warning instead of failing at delivery time
@pytest.mark.parametrize("setting, value", [
    ("WEBHOOK_URL", "your_webhook_url"),
    ("WEBHOOK_PROVIDER", "slack"),
    ("WEBHOOK_AVATAR_URL", "not-a-url"),
    ("WEBHOOK_HEADERS", {"Bad Header": "value"}),
])
def test_an_unusable_webhook_setting_warns(pm_module, monkeypatch, setting, value):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", WEBHOOK_URL)
    monkeypatch.setattr(pm_module, "WEBHOOK_ERROR_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, setting, value)
    report = pm_module.DoctorReport()

    check = pm_module.doctor_check_webhook_notifications(report)[0]

    assert check.status == "WARN"
    assert report.webhook_ready is False


# Verifies a usable channel names the service and the alerts without printing the private destination
def test_a_usable_webhook_names_the_service_without_the_private_url(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", WEBHOOK_URL)
    monkeypatch.setattr(pm_module, "WEBHOOK_GAME_CHANGE_NOTIFICATION", True)
    report = pm_module.DoctorReport()

    check = pm_module.doctor_check_webhook_notifications(report)[0]

    assert check.status == "PASS"
    assert "Discord" in check.label
    assert check.label.startswith(pm_module.WEBHOOK_READY_CHECK_LABEL)
    assert "game changes" in check.detail
    assert "aVeryLongWebhookTokenValue" not in check.detail
    assert "discord.com" not in check.detail
    assert report.webhook_ready is True


# Verifies both channels are reported, so one being unusable never hides the state of the other
def test_both_channels_are_reported_together(pm_module, monkeypatch, smtp_sign_in_ok):
    monkeypatch.setattr(pm_module, "GAME_CHANGE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", WEBHOOK_URL)
    monkeypatch.setattr(pm_module, "WEBHOOK_GAME_CHANGE_NOTIFICATION", True)
    report = pm_module.DoctorReport()

    checks = pm_module.doctor_check_notifications(report)

    assert len(checks) == 2
    assert (report.email_ready, report.webhook_ready) == (True, True)


# Verifies a declined delivery test is recorded as skipped and sends nothing
def test_a_declined_delivery_test_sends_nothing(pm_module, monkeypatch, sent_emails):
    monkeypatch.setattr(pm_module, "ask_yes_no", lambda question, default=False: False)
    monkeypatch.setattr(pm_module.sys, "stdin", FakeTerminal())
    monkeypatch.setattr(pm_module.sys, "stdout", FakeTerminal())
    report = pm_module.DoctorReport(email_ready=True)

    checks = pm_module.offer_doctor_delivery_tests(report)

    assert [check.status for check in checks] == ["SKIP"]
    assert sent_emails == []


# Verifies an approved delivery test sends exactly one real message and reports the outcome
def test_an_approved_delivery_test_sends_one_message(pm_module, monkeypatch, sent_emails):
    monkeypatch.setattr(pm_module, "ask_yes_no", lambda question, default=False: True)
    monkeypatch.setattr(pm_module.sys, "stdin", FakeTerminal())
    monkeypatch.setattr(pm_module.sys, "stdout", FakeTerminal())
    report = pm_module.DoctorReport(email_ready=True)

    checks = pm_module.offer_doctor_delivery_tests(report)

    assert [check.status for check in checks] == ["PASS"]
    assert len(sent_emails) == 1


# Verifies each ready channel is offered its own approval, and only the approved one delivers
def test_each_ready_channel_is_approved_separately(pm_module, monkeypatch, sent_emails, sent_webhooks):
    answers = {"email": True, "webhook": False}
    monkeypatch.setattr(pm_module, "ask_yes_no", lambda question, default=False: answers["webhook"] if "webhook" in question else answers["email"])
    monkeypatch.setattr(pm_module.sys, "stdin", FakeTerminal())
    monkeypatch.setattr(pm_module.sys, "stdout", FakeTerminal())
    report = pm_module.DoctorReport(email_ready=True, webhook_ready=True)

    checks = pm_module.offer_doctor_delivery_tests(report)

    assert [check.status for check in checks] == ["PASS", "SKIP"]
    assert len(sent_emails) == 1
    assert sent_webhooks == []


# Verifies an approved webhook test sends exactly one real notification through the ready channel
def test_an_approved_webhook_test_sends_one_notification(pm_module, monkeypatch, sent_webhooks):
    monkeypatch.setattr(pm_module, "ask_yes_no", lambda question, default=False: True)
    monkeypatch.setattr(pm_module.sys, "stdin", FakeTerminal())
    monkeypatch.setattr(pm_module.sys, "stdout", FakeTerminal())
    report = pm_module.DoctorReport(webhook_ready=True)

    checks = pm_module.offer_doctor_delivery_tests(report)

    assert [check.status for check in checks] == ["PASS"]
    assert len(sent_webhooks) == 1
    assert sent_webhooks[0]["force"] is True


# Verifies nothing is offered when the output is redirected, where no one could answer the prompt
def test_no_delivery_test_is_offered_without_a_terminal(pm_module, monkeypatch, sent_emails):
    monkeypatch.setattr(pm_module.sys, "stdin", FakeTerminal(interactive=False))
    monkeypatch.setattr(pm_module.sys, "stdout", FakeTerminal(interactive=False))

    assert pm_module.offer_doctor_delivery_tests(pm_module.DoctorReport(email_ready=True)) == []
    assert sent_emails == []


# Verifies a healthy setup exits zero, so the doctor can gate a deployment script
def test_a_healthy_setup_exits_zero(pm_module, psn_session, doctor_run):
    psn_session([presence_payload(status="online")])

    code, _ = doctor_run(interactive=False, psn_user_id=USER_ID)

    assert code == 0


# Verifies any failure exits one, and that a warning on its own does not
def test_only_a_failure_changes_the_exit_code(pm_module, psn_session, doctor_run, monkeypatch):
    psn_session([presence_payload(status="online")])
    monkeypatch.setattr(pm_module, "PSN_ACTIVE_CHECK_INTERVAL", 5)

    warned, raw = doctor_run(interactive=False, psn_user_id=USER_ID)
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "")
    failed, _ = doctor_run(interactive=False, psn_user_id=USER_ID)

    assert "[WARN]" in as_displayed(raw)
    assert (warned, failed) == (0, 1)


# Runs main() with the supplied command line and returns the exit code it raised
def run_main(pm_module, monkeypatch, argv):
    monkeypatch.setattr(pm_module.sys, "argv", ["psn_monitor", *argv])
    with pytest.raises(SystemExit) as raised:
        pm_module.main()
    return raised.value.code


# Verifies a configuration file that cannot be loaded becomes a report row instead of stopping the run
def test_a_broken_configuration_file_is_reported_not_fatal(pm_module, psn_session, monkeypatch, capsys, tmp_path):
    psn_session([presence_payload(status="online")])
    broken = tmp_path / "broken.conf"
    broken.write_text("PSN_CHECK_INTERVAL = os.system('id')\n", encoding="utf-8")

    code = run_main(pm_module, monkeypatch, [USER_ID, "--doctor", "--config-file", str(broken), "--env-file", "none"])

    output = capsys.readouterr().out
    assert code == 1
    assert "[FAIL] Config file" in output
    # The rest of the report still ran, which is the point of not exiting on the first problem
    assert "Authentication" in output and "Summary" in output


# Verifies an invalid time zone becomes a report row, and the report still stamps its own timestamps
def test_an_invalid_timezone_is_reported_not_fatal(pm_module, psn_session, monkeypatch, capsys):
    psn_session([presence_payload(status="online")])
    monkeypatch.setattr(pm_module, "LOCAL_TIMEZONE", "Mars/Olympus_Mons")

    code = run_main(pm_module, monkeypatch, [USER_ID, "--doctor", "--env-file", "none"])

    output = capsys.readouterr().out
    assert code == 1
    assert "[FAIL] Local timezone is invalid\n  Mars/Olympus_Mons" in output
    assert "Notifications" in output


# Verifies the same invalid time zone still stops a normal run, since monitoring cannot timestamp anything
def test_an_invalid_timezone_still_stops_a_normal_run(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "LOCAL_TIMEZONE", "Mars/Olympus_Mons")

    code = run_main(pm_module, monkeypatch, [USER_ID, "--env-file", "none"])

    assert code == 1
    assert "is not valid" in capsys.readouterr().out


# Verifies the report names the status file it would write, so a bad destination is found before monitoring
def test_the_report_names_the_status_file(pm_module, doctor_run, monkeypatch, tmp_path):
    destination = tmp_path / "last_status.json"
    monkeypatch.setattr(pm_module, "PSN_STATUS_FILE", str(destination))

    _, raw = doctor_run(psn_user_id=USER_ID)

    assert "[PASS] Status file is writable" in raw
    assert str(destination) in raw


# Verifies a row whose advice repeats its own summary prints that text once rather than as two problems
def test_a_row_never_prints_its_summary_twice(pm_module):
    repeated = "WEBHOOK_URL must contain a complete HTTPS link"

    check = pm_module.make_doctor_check("Notifications", "WARN", repeated, repeated)

    assert check.label == repeated
    assert check.detail == ""
    assert pm_module.render_doctor_sections(pm_module.DoctorReport(checks=[check])).count(repeated) == 1


# Verifies the Python row states the minimum it was judged against, whichever way the judgement went
def test_the_python_row_names_the_minimum_supported_version(pm_module):
    too_old = (pm_module.MINIMUM_PYTHON_VERSION[0], pm_module.MINIMUM_PYTHON_VERSION[1] - 1, 0)

    supported = pm_module.doctor_check_environment()[0]
    unsupported = pm_module.doctor_check_environment(version_info=too_old)[0]

    assert supported.detail == f"Minimum supported version: {pm_module.MINIMUM_PYTHON_VERSION_TEXT}"
    assert unsupported.detail == supported.detail


# Verifies settings that are merely valid take no row, since a value that is fine is not a finding
def test_valid_intervals_and_separators_take_no_row(pm_module):
    labels = [check.label for check in pm_module.doctor_check_configuration()]

    assert "Check intervals are set" not in labels
    assert not any(label.startswith("ASCII log separators") for label in labels)


# Verifies every doctor detail keeps to the agreed shapes: it never repeats its label, gives an instruction or joins values with a pipe
def test_doctor_details_keep_to_the_agreed_shapes(pm_module):
    import ast
    import inspect

    # Renders one detail argument as text, standing in {} for the parts an f-string fills at runtime
    def detail_text(node):
        if isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, str) else None
        if isinstance(node, ast.JoinedStr):
            return "".join(part.value if isinstance(part, ast.Constant) else "{}" for part in node.values)
        return None

    offenders = []
    for node in ast.walk(ast.parse(inspect.getsource(pm_module))):
        if not isinstance(node, ast.Call) or ast.unparse(node.func) not in {"make_doctor_check", "report.add"} or len(node.args) < 4:
            continue
        label, text = node.args[2], detail_text(node.args[3])
        if text is None:
            continue
        if isinstance(label, ast.Constant) and text == label.value:
            offenders.append(f"{node.lineno}: the detail repeats its label")
        if text.startswith(("Use ", "Set ", "Run ")):
            offenders.append(f"{node.lineno}: the detail gives an instruction, which belongs in the fix line")
        if " | " in text:
            offenders.append(f"{node.lineno}: the detail joins two values with a pipe")
        if text.endswith("."):
            offenders.append(f"{node.lineno}: the detail ends with a full stop")

    assert not offenders, "doctor details outside the agreed shapes:\n" + "\n".join(offenders)


# Verifies the resolved time zone is reported as a named value rather than a bare string
def test_the_timezone_row_names_the_value(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "LOCAL_TIMEZONE", "Europe/Warsaw")
    monkeypatch.setattr(pm_module, "LOCAL_TIMEZONE_STATE", "config")

    checks = pm_module.doctor_check_configuration()

    check = next(item for item in checks if item.label == pm_module.TIMEZONE_CHECK_LABELS["config"])
    assert check.detail == "Time zone: Europe/Warsaw"


# Verifies the constructor drops a detail that only repeats its label, so no row says the same thing twice
def test_a_detail_that_repeats_its_label_is_dropped(pm_module):
    check = pm_module.make_doctor_check("Configuration", "PASS", "Output logging is disabled", "Output logging is disabled")

    assert check.detail == ""


# Verifies only the four shared markers can reach a report
def test_only_the_four_shared_markers_are_accepted(pm_module):
    assert pm_module.DOCTOR_STATUSES == MARKERS
    assert [pm_module.make_doctor_check("Configuration", status, "a label").status for status in MARKERS] == list(MARKERS)

    with pytest.raises(ValueError):
        pm_module.make_doctor_check("Configuration", "INFO", "a label")


# Verifies one row reads as one block: the action lines sit under the marker at the detail indent while a pass row has none
def test_the_action_lines_sit_indented_under_their_marker(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "colorize", lambda theme, text: text)
    advice = pm_module.make_recovery_advice("unknown", "a summary", pm_module.recovery_fix_with_guide("do the thing", pm_module.DOCTOR_GUIDE_URL), True)
    report = pm_module.DoctorReport([
        pm_module.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping", advice),
        pm_module.make_doctor_check("Configuration", "PASS", "a passing row", "", advice),
    ])

    lines = pm_module.render_doctor_sections(report).splitlines()
    rows = lines[lines.index("[WARN] a warning row"):]

    assert rows[:5] == ["[WARN] a warning row", "  a detail worth keeping", "  To fix: do the thing", f"  Guide: {pm_module.DOCTOR_GUIDE_URL}", "[PASS] a passing row"]


# Verifies an approved delivery test that failed reaches the summary, so a failing run cannot report a clean one
def test_a_failed_delivery_test_reaches_the_summary(pm_module, monkeypatch):
    terminal = FakeTerminal(True)
    monkeypatch.setattr(pm_module.sys, "stdout", terminal)
    monkeypatch.setattr(pm_module.sys, "stdin", terminal)
    monkeypatch.setattr(pm_module, "ask_yes_no", lambda question: True)
    monkeypatch.setattr(pm_module, "send_email", lambda *args, **kwargs: 1)
    report = pm_module.DoctorReport(email_ready=True)

    pm_module.offer_doctor_delivery_tests(report)

    assert [(check.section, check.status, check.label) for check in report.checks] == [(pm_module.DOCTOR_DELIVERY_SECTION, "FAIL", "Doctor test email delivery failed")]
    assert "1 check(s) failed, 0 warning(s)." in pm_module.render_doctor_summary(report.checks)


# Verifies every doctor entry point renders its summary after the delivery tests, so the sentence and the exit code describe one run
def test_the_summary_is_rendered_after_the_delivery_tests(pm_module):
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(pm_module))
    checked = 0
    for function in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
        calls = [(call.lineno, ast.unparse(call.func)) for call in ast.walk(function) if isinstance(call, ast.Call)]
        offers = [lineno for lineno, name in calls if name.endswith("offer_doctor_delivery_tests")]
        summaries = [lineno for lineno, name in calls if name.endswith("render_doctor_summary")]
        if not offers or not summaries:
            continue
        checked += 1
        assert max(offers) < min(summaries), f"{function.name} renders the summary before the delivery tests"

    assert checked, "no doctor entry point runs the delivery tests and then the summary"
