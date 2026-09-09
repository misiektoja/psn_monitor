"""Tests for the one-shot secret commands and the dotenv file they write."""

import smtplib
import stat

import pytest

import psn_monitor as monitor


NPSSO = "a-fresh-npsso-code"
SMTP_SECRET = "aVeryLongSmtpPassword123"
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"


# Stands in for smtplib.SMTP and records the sign-in the tool attempts
class SignInSMTP:
    last = None

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_args = None
        self.quit_called = False
        self.sent = False
        SignInSMTP.last = self

    # Records that the connection was upgraded to TLS
    def starttls(self, context=None):
        self.started_tls = True

    # Records the credentials the tool authenticated with
    def login(self, user, password):
        self.login_args = (user, password)

    # Fails the test if a check ever delivers a message
    def sendmail(self, *args, **kwargs):
        self.sent = True
        raise AssertionError("checking a password must not send anything")

    # Records that the session was closed
    def quit(self):
        self.quit_called = True


@pytest.fixture
# Replaces the SMTP client with the recording double
def smtp_double(monkeypatch, pm_module):
    SignInSMTP.last = None
    monkeypatch.setattr(pm_module.smtplib, "SMTP", SignInSMTP)
    return SignInSMTP


@pytest.fixture
# Replaces PSN with the shared offline double, so checking a code never leaves the machine
def psn_double(psn_session):
    return psn_session


# Verifies an existing assignment is replaced in place rather than appended a second time
def test_an_existing_assignment_is_replaced_in_place(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('PSN_NPSSO="old-code"\nSMTP_PASSWORD="unrelated"\n', encoding="utf-8")

    monitor.update_dotenv_value(env_file, "PSN_NPSSO", "new-code")

    lines = env_file.read_text(encoding="utf-8").splitlines()
    assert lines == ['PSN_NPSSO="new-code"', 'SMTP_PASSWORD="unrelated"']


# Verifies an exported line keeps its prefix, since a second assignment would leave the old credential on disk
def test_an_exported_assignment_keeps_its_prefix(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('export PSN_NPSSO="old-code"\n', encoding="utf-8")

    monitor.update_dotenv_value(env_file, "PSN_NPSSO", "new-code")

    content = env_file.read_text(encoding="utf-8")
    assert content == 'export PSN_NPSSO="new-code"\n'
    assert content.count("PSN_NPSSO") == 1


# Verifies comments and unrelated lines survive a rotation untouched
def test_unrelated_lines_survive_the_rotation(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('# keep me\n# PSN_NPSSO="commented out"\nSMTP_PASSWORD="unrelated"\n', encoding="utf-8")

    monitor.update_dotenv_value(env_file, "PSN_NPSSO", "new-code")

    lines = env_file.read_text(encoding="utf-8").splitlines()
    assert lines == ["# keep me", '# PSN_NPSSO="commented out"', 'SMTP_PASSWORD="unrelated"', 'PSN_NPSSO="new-code"']


# Verifies a value with quotes or backslashes is written so python-dotenv reads it back unchanged
def test_a_value_with_quotes_is_escaped(tmp_path):
    env_file = tmp_path / ".env"

    monitor.update_dotenv_value(env_file, "SMTP_PASSWORD", 'pa"ss\\word')

    assert env_file.read_text(encoding="utf-8") == 'SMTP_PASSWORD="pa\\"ss\\\\word"\n'
    dotenv = pytest.importorskip("dotenv")
    assert dotenv.dotenv_values(str(env_file))["SMTP_PASSWORD"] == 'pa"ss\\word'


# Verifies a dotenv file the tool creates is readable only by its owner
def test_a_written_dotenv_file_is_private(tmp_path):
    env_file = tmp_path / ".env"

    monitor.update_dotenv_value(env_file, "PSN_NPSSO", "new-code")

    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert [entry.name for entry in tmp_path.iterdir()] == [".env"]


# Verifies a commented assignment does not count as the key being set
def test_a_commented_assignment_does_not_count_as_set(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('# PSN_NPSSO="commented out"\n', encoding="utf-8")

    assert monitor.dotenv_contains_key(env_file, "PSN_NPSSO") is False


# Verifies an exported assignment does count as the key being set
def test_an_exported_assignment_counts_as_set(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('export PSN_NPSSO="set"\n', encoding="utf-8")

    assert monitor.dotenv_contains_key(env_file, "PSN_NPSSO") is True


# Verifies a hidden entry cannot be asked for when there is no terminal to hide it from
def test_setting_a_secret_needs_a_terminal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_npsso(interactive=False)

    assert raised.value.advice.code == "secret.entry"
    assert not (tmp_path / ".env").exists()


# Verifies a dotenv file that was explicitly disabled is not silently created somewhere else
def test_setting_a_secret_refuses_a_disabled_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_npsso(env_file="none", interactive=True)

    assert raised.value.advice.code == "secret.entry"
    assert list(tmp_path.iterdir()) == []


# Verifies a validated NPSSO code is written and the account it signed in as is reported
def test_a_validated_npsso_code_is_saved(tmp_path, monkeypatch, psn_double, capsys):
    env_file = tmp_path / ".env"

    monitor.run_set_npsso(env_file=str(env_file), interactive=True, getpass_func=lambda prompt: NPSSO)

    assert env_file.read_text(encoding="utf-8") == f'PSN_NPSSO="{NPSSO}"\n'
    output = capsys.readouterr().out
    assert "signed in as signed-in-account" in output
    assert NPSSO not in output


# Verifies a code PSN rejects is never written, so a working setup is not replaced by a broken one
def test_a_rejected_npsso_code_is_not_saved(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('PSN_NPSSO="working-code"\n', encoding="utf-8")

    def refuse(npsso):
        raise RuntimeError("PSN said no")

    monkeypatch.setattr(monitor, "PSNAWP", refuse)

    with pytest.raises(monitor.RecoveryError):
        monitor.run_set_npsso(env_file=str(env_file), interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: "bad-code")

    assert env_file.read_text(encoding="utf-8") == 'PSN_NPSSO="working-code"\n'


# Verifies replacing a secret that is already set has to be confirmed first
def test_replacing_an_existing_secret_is_confirmed(tmp_path, psn_double):
    env_file = tmp_path / ".env"
    env_file.write_text('PSN_NPSSO="working-code"\n', encoding="utf-8")

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_npsso(env_file=str(env_file), interactive=True, input_func=lambda prompt: "n", getpass_func=lambda prompt: NPSSO)

    assert raised.value.advice.code == "secret.entry"
    assert env_file.read_text(encoding="utf-8") == 'PSN_NPSSO="working-code"\n'


# Verifies an empty answer is refused instead of writing a blank secret over a working one
def test_an_empty_answer_is_refused(tmp_path, psn_double):
    env_file = tmp_path / ".env"

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_npsso(env_file=str(env_file), interactive=True, getpass_func=lambda prompt: "   ")

    assert raised.value.advice.code == "secret.entry"
    assert not env_file.exists()


# Verifies the password is checked by signing in to the mail server, and that nothing is delivered
def test_the_smtp_password_is_checked_by_signing_in(tmp_path, smtp_double, capsys):
    env_file = tmp_path / ".env"

    monitor.run_set_smtp_password(env_file=str(env_file), interactive=True, getpass_func=lambda prompt: SMTP_SECRET)

    assert smtp_double.last.login_args == ("monitor@example.test", SMTP_SECRET)
    assert smtp_double.last.started_tls is True
    assert smtp_double.last.quit_called is True
    assert smtp_double.last.sent is False
    assert env_file.read_text(encoding="utf-8") == f'SMTP_PASSWORD="{SMTP_SECRET}"\n'


# Verifies a password the mail server rejects is never written
def test_a_rejected_smtp_password_is_not_saved(tmp_path, monkeypatch, pm_module):
    env_file = tmp_path / ".env"

    class RejectingSMTP(SignInSMTP):
        def login(self, user, password):
            raise smtplib.SMTPAuthenticationError(535, "rejected")

    monkeypatch.setattr(pm_module.smtplib, "SMTP", RejectingSMTP)

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_smtp_password(env_file=str(env_file), interactive=True, getpass_func=lambda prompt: "wrong")

    assert raised.value.advice.code == "smtp.authentication"
    assert not env_file.exists()


# Verifies the candidate password is not left behind in the module after a check
def test_the_candidate_password_does_not_stay_applied(tmp_path, monkeypatch, pm_module, smtp_double):
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "configured-password")

    monitor.run_set_smtp_password(env_file=str(tmp_path / ".env"), interactive=True, getpass_func=lambda prompt: SMTP_SECRET)

    assert pm_module.SMTP_PASSWORD == "configured-password"


# Verifies the entered secret never reaches the debug stream, which prints everything else verbatim
def test_the_entered_secret_is_not_printed_under_debug(tmp_path, monkeypatch, pm_module, psn_double, capsys):
    monkeypatch.setattr(pm_module, "DEBUG_MODE", True)
    seen = []

    monitor.run_set_npsso(env_file=str(tmp_path / ".env"), interactive=True, getpass_func=lambda prompt: seen.append(pm_module.DEBUG_MODE) or NPSSO)

    assert seen == [False], "debug output must be off while the value is entered"
    assert pm_module.DEBUG_MODE is True
    assert NPSSO not in capsys.readouterr().out


# Verifies the next commands are printed with the paths this run was given, so they can be pasted as they are
def test_the_next_steps_carry_the_files_that_were_used(tmp_path, psn_double, capsys):
    env_file = tmp_path / "secrets.env"

    monitor.run_set_npsso(env_file=str(env_file), config_path="psn_monitor.conf", psn_user_id="misiektoja", interactive=True, getpass_func=lambda prompt: NPSSO)

    output = capsys.readouterr().out
    assert "--doctor misiektoja" in output
    assert "--config-file psn_monitor.conf" in output
    assert f"--env-file {env_file}" in output


# Verifies an empty password is reported as nothing entered rather than as a broken SMTP configuration
def test_an_empty_smtp_password_is_refused(tmp_path, smtp_double):
    env_file = tmp_path / ".env"

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_smtp_password(env_file=str(env_file), interactive=True, getpass_func=lambda prompt: "")

    assert raised.value.advice.code == "secret.entry"
    assert smtp_double.last is None
    assert not env_file.exists()


# Verifies a valid webhook URL is written and the service it points at is named back
def test_a_valid_webhook_url_is_saved(tmp_path, capsys):
    env_file = tmp_path / ".env"

    monitor.run_set_webhook_url(env_file=str(env_file), interactive=True, getpass_func=lambda prompt: WEBHOOK_URL)

    assert env_file.read_text(encoding="utf-8") == f'WEBHOOK_URL="{WEBHOOK_URL}"\n'
    output = capsys.readouterr().out
    assert "valid Discord destination" in output
    assert WEBHOOK_URL not in output


# Verifies an ntfy topic name is expanded before it is stored, so the saved value is a complete URL
def test_an_ntfy_topic_name_is_saved_as_a_complete_url(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    env_file = tmp_path / ".env"

    monitor.run_set_webhook_url(env_file=str(env_file), interactive=True, getpass_func=lambda prompt: "private-topic")

    assert env_file.read_text(encoding="utf-8") == 'WEBHOOK_URL="https://ntfy.sh/private-topic"\n'


# Verifies a destination that is not a complete HTTPS link never replaces a working one
def test_an_unusable_webhook_url_is_not_saved(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(f'WEBHOOK_URL="{WEBHOOK_URL}"\n', encoding="utf-8")

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_webhook_url(env_file=str(env_file), interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: "http://discord.com/api/webhooks/1/token")

    assert raised.value.advice.code == "webhook.invalid"
    assert env_file.read_text(encoding="utf-8") == f'WEBHOOK_URL="{WEBHOOK_URL}"\n'


# Verifies a URL for the other service is refused rather than silently saved against the wrong provider
def test_a_url_for_the_other_service_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    env_file = tmp_path / ".env"

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_webhook_url(env_file=str(env_file), interactive=True, getpass_func=lambda prompt: WEBHOOK_URL)

    assert raised.value.advice.code == "webhook.invalid"
    assert "WEBHOOK_PROVIDER" in raised.value.advice.detail
    assert not env_file.exists()


# Verifies an empty answer is reported as nothing entered rather than as a broken destination
def test_an_empty_webhook_url_is_refused(tmp_path):
    env_file = tmp_path / ".env"

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_webhook_url(env_file=str(env_file), interactive=True, getpass_func=lambda prompt: "   ")

    assert raised.value.advice.code == "secret.entry"
    assert not env_file.exists()


# Verifies a destination that was only checked offline is followed by the delivery test that does confirm it
def test_a_saved_webhook_url_names_the_delivery_test(tmp_path, capsys):
    monitor.run_set_webhook_url(env_file=str(tmp_path / ".env"), interactive=True, getpass_func=lambda prompt: WEBHOOK_URL)

    output = capsys.readouterr().out
    assert "Send a test webhook:" in output
    assert "--send-test-webhook" in output
    assert output.index("Send a test webhook:") < output.index("Check setup again:")


# Verifies a secret the live service already accepted is not followed by a delivery test it does not need
def test_a_saved_npsso_code_names_no_delivery_test(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(monitor, "validate_npsso_code", lambda code: "signed-in-account")

    monitor.run_set_npsso(env_file=str(tmp_path / ".env"), interactive=True, getpass_func=lambda prompt: "a-fresh-npsso-code")

    assert "Send a test" not in capsys.readouterr().out


# Verifies an interrupted entry reports the cancel itself, with the command that resumes it
def test_an_interrupted_secret_entry_reports_the_cancel(tmp_path, monkeypatch):
    destination = tmp_path / ".env"
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor@example.test")

    def interrupt(prompt=""):
        raise KeyboardInterrupt

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_smtp_password(env_file=str(destination), interactive=True, getpass_func=interrupt)

    advice = raised.value.advice
    assert advice.summary == "SMTP password setup was cancelled and the dotenv file was not changed"
    assert "Run --set-smtp-password again when you have the value ready" in advice.fix
    assert monitor.SMTP_GUIDE_URL in advice.fix
    assert not destination.exists()


# Verifies a declined replacement reports the kept value rather than a cancelled entry
def test_a_declined_secret_replacement_reports_the_kept_value(tmp_path, monkeypatch):
    destination = tmp_path / ".env"
    destination.write_text('SMTP_PASSWORD="original"\n', encoding="utf-8")
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor@example.test")

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_smtp_password(env_file=str(destination), interactive=True, input_func=lambda prompt: "n", getpass_func=lambda prompt: pytest.fail("hidden prompt used"))

    advice = raised.value.advice
    assert advice.summary == "The saved SMTP password was left as it is and the dotenv file was not changed"
    assert "answer y to replace the saved value" in advice.fix
    assert destination.read_text(encoding="utf-8") == 'SMTP_PASSWORD="original"\n'


PROGRESS_COMMANDS = (("run_set_npsso", "NPSSO code", NPSSO), ("run_set_webhook_url", "webhook URL", WEBHOOK_URL), ("run_set_smtp_password", "SMTP password", SMTP_SECRET))


# Verifies each secret command announces the check the way the siblings do, naming the dotenv file rather than its path
@pytest.mark.parametrize("command_name, subject, secret", PROGRESS_COMMANDS)
def test_the_progress_line_names_the_dotenv_file_not_its_path(command_name, subject, secret, tmp_path, psn_double, smtp_double, capsys):
    env_file = tmp_path / ".env"

    getattr(monitor, command_name)(env_file=str(env_file), interactive=True, getpass_func=lambda prompt: secret)

    line = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("* Checking the entered"))
    assert line == f"* Checking the entered {subject} before changing the dotenv file ..."
