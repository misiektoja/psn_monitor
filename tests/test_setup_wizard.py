"""Tests for the guided setup: what it asks, what it writes and when it writes nothing."""

import re

import signal
import types
import pytest

import psn_monitor as monitor


USER_ID = "misiektoja"
NPSSO = "a-fresh-npsso-code"
SMTP_SECRET = "aVeryLongSmtpPassword123"
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"


@pytest.fixture(autouse=True)
# Keeps the wizard's mail server sign-in check offline, so a scripted run never opens a connection
def accepted_smtp_sign_in(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: None)


# Replays scripted answers the way a terminal does, echoing each prompt so the transcript is what a user sees
class ScriptedTerminal:
    def __init__(self, *script, secrets=None):
        self.remaining = list(script)
        self.prompts = []
        self.secrets = secrets if secrets is not None else (lambda prompt: NPSSO if "NPSSO" in prompt else SMTP_SECRET)

    # Answers one visible prompt, raising EOFError once the script runs out so a wrong question cannot hang
    def answer(self, prompt):
        self.prompts.append(prompt)
        if not self.remaining:
            raise EOFError(f"the wizard asked more than the script answers: {prompt!r}")
        typed = self.remaining.pop(0)
        print(f"{prompt}{typed}")
        return typed

    # Answers one hidden prompt, echoing only the prompt, since a terminal never shows the value
    def secret(self, prompt):
        self.prompts.append(prompt)
        print(prompt)
        return self.secrets(prompt)

    # Reports whether any prompt contained the given text
    def asked(self, text):
        return any(text in prompt for prompt in self.prompts)


# Replays scripted answers and then interrupts the next prompt, the way Ctrl+C does
class InterruptedTerminal(ScriptedTerminal):
    # Interrupts instead of running out of answers, so a test can cancel at a chosen prompt
    def answer(self, prompt):
        if not self.remaining:
            raise KeyboardInterrupt
        return super().answer(prompt)


# Runs the wizard against one scripted terminal and returns it, so a test can assert on what was asked
def run_wizard(terminal, **kwargs):
    kwargs.setdefault("interactive", True)
    exit_code = monitor.run_setup_wizard(input_func=terminal.answer, getpass_func=terminal.secret, **kwargs)
    return exit_code


# Returns the answers for one complete run that saves, with the pieces a test wants to vary
def happy_path(target=USER_ID, persist="", save="1", doctor="n", monitor_now="n"):
    return (
        target, persist,               # target and whether to save it
        "", "",                        # both polling intervals keep their defaults
        "y",                           # configure email
        "smtp.example.test", "587", "y", "monitor@example.test", "monitor@example.test", "alerts@example.test",
        "1",                           # the recommended notification preset
        "n",                           # no webhook alerts
        "y", "", "",                   # keep the log, no CSV, default status file
        save, doctor, monitor_now,
    )


@pytest.fixture(autouse=True)
# Keeps every generated file inside the test directory and starts from an unconfigured setup
def wizard_environment(tmp_path, monkeypatch, pm_module, psn_session):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "")
    monkeypatch.setattr(pm_module, "PSN_USER_ID", "")
    monkeypatch.setattr(pm_module, "DEFAULT_CONFIG_FILENAME", "psn_monitor.conf")
    return tmp_path


# Verifies setup refuses without a terminal and names the command that works instead
def test_setup_needs_a_terminal(tmp_path, capsys):
    assert monitor.run_setup_wizard(interactive=False) == 1

    output = capsys.readouterr().out
    assert "interactive terminal" in output
    assert "--generate-config" in output
    assert list(tmp_path.iterdir()) == []


# Verifies setup refuses when the dotenv file it needs was explicitly switched off
def test_setup_refuses_a_disabled_dotenv(tmp_path, capsys):
    assert monitor.run_setup_wizard(env_file="none", interactive=True) == 1

    assert "--env-file none" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


# Verifies a complete run writes both files and reports where each one went
def test_a_saved_run_writes_the_config_and_the_secrets(tmp_path, capsys):
    exit_code = run_wizard(ScriptedTerminal(*happy_path()))

    assert exit_code == 0
    config = (tmp_path / "psn_monitor.conf").read_text(encoding="utf-8")
    values = monitor.parse_config_content(config, "psn_monitor.conf")
    assert values["PSN_USER_ID"] == USER_ID
    assert values["SMTP_HOST"] == "smtp.example.test"
    assert values["ACTIVE_INACTIVE_NOTIFICATION"] is True
    env = (tmp_path / ".env").read_text(encoding="utf-8")
    assert f'PSN_NPSSO="{NPSSO}"' in env
    assert f'SMTP_PASSWORD="{SMTP_SECRET}"' in env
    output = capsys.readouterr().out
    assert "Saved files" in output
    assert "Next steps" in output


# Verifies no secret ever reaches the screen, including in the summary that lists everything else
def test_the_summary_never_prints_a_secret(capsys):
    run_wizard(ScriptedTerminal(*happy_path()))

    output = capsys.readouterr().out
    assert NPSSO not in output
    assert SMTP_SECRET not in output
    assert "Authentication status" in output


# Verifies nothing reaches disk when the answers are discarded
def test_discarding_writes_nothing(tmp_path, capsys):
    exit_code = run_wizard(ScriptedTerminal(*happy_path(save="3")[:-2], "y"))

    assert exit_code == 1
    assert list(tmp_path.iterdir()) == []
    assert "were not changed" in capsys.readouterr().out


# Verifies discarding takes a second confirmation, so one mistyped menu number cannot throw the answers away
def test_discarding_is_confirmed_twice(tmp_path):
    script = happy_path(save="3")[:-2] + ("n", "1", "n", "n")

    exit_code = run_wizard(ScriptedTerminal(*script))

    assert exit_code == 0
    assert (tmp_path / "psn_monitor.conf").is_file()


# Verifies editing one section keeps every answer the other sections collected
def test_editing_one_section_keeps_the_other_answers(tmp_path):
    # Save is answer 2 in the review menu: change the polling section, then save
    script = happy_path(save="2")[:-2] + ("2", "300", "600", "1", "n", "n")

    run_wizard(ScriptedTerminal(*script))

    values = monitor.parse_config_content((tmp_path / "psn_monitor.conf").read_text(encoding="utf-8"), "psn_monitor.conf")
    assert values["PSN_CHECK_INTERVAL"] == 300
    assert values["PSN_ACTIVE_CHECK_INTERVAL"] == 600
    assert values["PSN_USER_ID"] == USER_ID
    assert values["SMTP_HOST"] == "smtp.example.test"


# Verifies a target that is not saved stays out of the config and is carried by the printed commands instead
def test_a_target_that_is_not_saved_stays_out_of_the_config(tmp_path, capsys):
    run_wizard(ScriptedTerminal(*happy_path(persist="n")))

    values = monitor.parse_config_content((tmp_path / "psn_monitor.conf").read_text(encoding="utf-8"), "psn_monitor.conf")
    assert values["PSN_USER_ID"] == ""
    assert f"--doctor {USER_ID}" in capsys.readouterr().out


# Verifies the address mistake the target line warns about is caught with the same wording
def test_an_email_address_is_rejected_as_a_target(capsys):
    script = ("player@example.test", USER_ID) + happy_path()[1:]

    run_wizard(ScriptedTerminal(*script))

    output = capsys.readouterr().out
    assert "looks like an e-mail address" in output
    assert monitor.PSN_TARGET_FORMS in output


# Verifies a profile link is accepted, since that is what a browser gives you
def test_a_profile_link_is_accepted_as_a_target(tmp_path):
    run_wizard(ScriptedTerminal(*happy_path(target=f"https://psnprofiles.com/{USER_ID}")))

    values = monitor.parse_config_content((tmp_path / "psn_monitor.conf").read_text(encoding="utf-8"), "psn_monitor.conf")
    assert values["PSN_USER_ID"] == USER_ID


# Verifies an empty NPSSO answer is asked again rather than quietly leaving monitoring unusable
def test_an_empty_npsso_answer_is_asked_again():
    entered = ["", NPSSO]
    # The extra "n" answers "Continue without the NPSSO code?", which must default to keeping the setup usable
    script = happy_path()[:4] + ("n",) + happy_path()[4:]
    terminal = ScriptedTerminal(*script, secrets=lambda prompt: entered.pop(0) if "NPSSO" in prompt else SMTP_SECRET)

    run_wizard(terminal)

    assert entered == []
    assert terminal.asked("Continue without the NPSSO code?")


# Verifies a code PSN rejects is asked again instead of being written
def test_a_rejected_npsso_code_is_asked_again(tmp_path, monkeypatch):
    attempts = ["bad-code", NPSSO]

    def validator(code):
        if code == "bad-code":
            raise monitor.RecoveryError(monitor.classify_recovery_error(context="secret.entry", detail="PSN rejected that code"))
        return "signed-in-account"

    monkeypatch.setattr(monitor, "validate_npsso_code", validator)
    # The extra "y" accepts the offer to enter the rejected code again
    script = happy_path()[:4] + ("y",) + happy_path()[4:]

    terminal = ScriptedTerminal(*script, secrets=lambda prompt: attempts.pop(0) if "NPSSO" in prompt else SMTP_SECRET)
    run_wizard(terminal)

    assert attempts == []
    assert terminal.asked("Try entering the NPSSO code again?")
    assert f'PSN_NPSSO="{NPSSO}"' in (tmp_path / ".env").read_text(encoding="utf-8")


@pytest.mark.parametrize("typed,expected", [("120", 120), ("2m", 120), ("1.5h", 5400), ("1h 30m", 5400), ("1d", 86400)])
# Verifies the duration formats the prompt advertises are the ones it accepts
def test_the_advertised_duration_formats_are_accepted(typed, expected):
    assert monitor.parse_duration_input(typed) == expected


@pytest.mark.parametrize("typed", ["", "abc", "5x", "0", "-3"])
# Verifies anything else is refused rather than silently read as a number of seconds
def test_an_unparsable_duration_is_refused(typed):
    assert monitor.parse_duration_input(typed) is None


# Verifies a duration the parser rejects is asked again with the accepted formats named
def test_an_invalid_duration_is_asked_again(tmp_path, capsys):
    script = happy_path()[:2] + ("later", "300", "") + happy_path()[4:]

    run_wizard(ScriptedTerminal(*script))

    assert "1h 30m" in capsys.readouterr().out
    values = monitor.parse_config_content((tmp_path / "psn_monitor.conf").read_text(encoding="utf-8"), "psn_monitor.conf")
    assert values["PSN_CHECK_INTERVAL"] == 300


# Verifies the generated file is one the tool can read back, which is the only thing that makes setup useful
def test_the_generated_config_loads_through_the_parser(tmp_path):
    run_wizard(ScriptedTerminal(*happy_path()))

    namespace = {}
    assert monitor.load_config_file(str(tmp_path / "psn_monitor.conf"), namespace=namespace) is True
    assert namespace["PSN_USER_ID"] == USER_ID


# Verifies the wizard offers the check it just made possible, and reports it
def test_the_doctor_offer_runs_the_report(tmp_path, monkeypatch, capsys):
    ran = []
    monkeypatch.setattr(monitor, "run_doctor", lambda **kwargs: ran.append(kwargs) or 0)

    run_wizard(ScriptedTerminal(*happy_path(doctor="y")))

    assert ran and ran[0]["psn_user_id"] == USER_ID
    assert "Start monitoring:" in capsys.readouterr().out


# Verifies the wizard never prints two blank lines in a row, which is what the shared block rule comes down to
def test_the_wizard_output_has_no_double_blank_lines(capsys):
    run_wizard(ScriptedTerminal(*happy_path()))

    assert not re.search(r"\n[ \t]*\n[ \t]*\n", capsys.readouterr().out)


# Verifies the welcome screen offers the wizard on a terminal, with the suffix that names the prompt below
def test_the_welcome_screen_offers_the_wizard_on_a_terminal(capsys):
    terminal = ScriptedTerminal("n")

    assert monitor.print_welcome_screen(interactive=True, input_func=terminal.answer) == 0

    output = capsys.readouterr().out
    assert "Easiest start (guided setup wizard):" in output
    assert "(or just answer Y below)" in output
    assert terminal.asked("Run the guided setup wizard now?")


# Verifies the suffix and the offer both disappear when there is nobody to answer
def test_the_welcome_screen_makes_no_offer_without_a_terminal(capsys):
    def refuse_to_ask(prompt):
        raise AssertionError(f"nothing should have been asked: {prompt!r}")

    assert monitor.print_welcome_screen(interactive=False, input_func=refuse_to_ask) == 1

    output = capsys.readouterr().out
    assert "Easiest start (guided setup wizard):" in output
    assert "(or just answer Y below)" not in output


# Verifies answering yes at the welcome screen starts the wizard rather than only naming it
def test_answering_yes_at_the_welcome_screen_starts_the_wizard(monkeypatch, capsys):
    started = []
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **kwargs: started.append(kwargs) or 0)

    assert monitor.print_welcome_screen(interactive=True, input_func=lambda prompt: "y") == 0

    assert started


# Returns the answers up to and including the email preset, which every webhook run shares
def before_webhook_section():
    return (
        USER_ID, "",
        "", "",
        "y",
        "smtp.example.test", "587", "y", "monitor@example.test", "monitor@example.test", "alerts@example.test",
        "1",
    )


# Returns the answers that follow the webhook section, ending with a saved run
def after_webhook_section(save="1", doctor="n", monitor_now="n"):
    return ("y", "", "", "y", save, doctor, monitor_now)


# Answers each hidden prompt with the value that prompt asks for
def secrets_for(webhook_value):
    return lambda prompt: NPSSO if "NPSSO" in prompt else (webhook_value if "webhook" in prompt.casefold() or "topic" in prompt.casefold() else SMTP_SECRET)


# Verifies a configured Discord webhook writes its settings to the config and its URL to the dotenv file
def test_a_configured_webhook_is_saved(tmp_path):
    script = before_webhook_section() + ("y", "1", "1") + after_webhook_section()

    assert run_wizard(ScriptedTerminal(*script, secrets=secrets_for(WEBHOOK_URL))) == 0

    values = monitor.parse_config_content((tmp_path / "psn_monitor.conf").read_text(encoding="utf-8"), "psn_monitor.conf")
    assert values["WEBHOOK_ENABLED"] is True
    assert values["WEBHOOK_PROVIDER"] == "discord"
    assert values["WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION"] is True
    assert f'WEBHOOK_URL="{WEBHOOK_URL}"' in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies the private destination is never displayed, in the prompts or in the summary that lists everything else
def test_the_webhook_url_is_never_displayed(capsys):
    script = before_webhook_section() + ("y", "1", "1") + after_webhook_section()

    run_wizard(ScriptedTerminal(*script, secrets=secrets_for(WEBHOOK_URL)))

    output = capsys.readouterr().out
    assert WEBHOOK_URL not in output
    assert "Webhook:" in output
    assert "Webhook alerts:" in output


# Verifies an ntfy topic name is expanded before it is written, so the saved value is a complete URL
def test_an_ntfy_topic_name_is_saved_as_a_url(tmp_path):
    # The ntfy branch asks one extra question, whether the topic needs its own access token
    script = before_webhook_section() + ("y", "2", "n", "1") + after_webhook_section()

    assert run_wizard(ScriptedTerminal(*script, secrets=secrets_for("private-topic"))) == 0

    assert 'WEBHOOK_URL="https://ntfy.sh/private-topic"' in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies an ntfy access token is written only when one was asked for
def test_an_ntfy_access_token_is_saved_when_offered(tmp_path):
    script = before_webhook_section() + ("y", "2", "y", "1") + after_webhook_section()

    assert run_wizard(ScriptedTerminal(*script, secrets=lambda prompt: NPSSO if "NPSSO" in prompt else ("tk_a_real_looking_token" if "token" in prompt.casefold() else ("private-topic" if "topic" in prompt.casefold() else SMTP_SECRET)))) == 0

    assert 'NTFY_ACCESS_TOKEN="tk_a_real_looking_token"' in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies declining the webhook section leaves the channel and every alert it owns switched off
def test_declining_webhooks_turns_every_alert_off(tmp_path, monkeypatch):
    # The error alert ships on, so declining has to switch it off rather than carry the shipped default through
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_GAME_CHANGE_NOTIFICATION", True)

    run_wizard(ScriptedTerminal(*happy_path()))

    values = monitor.parse_config_content((tmp_path / "psn_monitor.conf").read_text(encoding="utf-8"), "psn_monitor.conf")
    assert values["WEBHOOK_ENABLED"] is False
    assert values["WEBHOOK_ERROR_NOTIFICATION"] is False
    assert values["WEBHOOK_GAME_CHANGE_NOTIFICATION"] is False


# Verifies an unusable destination is asked again, and that giving up leaves the channel off rather than looping
def test_an_unusable_webhook_url_can_be_abandoned(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    script = before_webhook_section() + ("y", "1", "n") + after_webhook_section()

    assert run_wizard(ScriptedTerminal(*script, secrets=secrets_for("not-a-url"))) == 0

    values = monitor.parse_config_content((tmp_path / "psn_monitor.conf").read_text(encoding="utf-8"), "psn_monitor.conf")
    assert values["WEBHOOK_ENABLED"] is False
    assert values["WEBHOOK_ERROR_NOTIFICATION"] is False
    assert "complete HTTPS webhook URL" in capsys.readouterr().out
    assert "WEBHOOK_URL" not in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies a blank destination is told apart from a malformed one and that skipping it leaves the channel off
def test_a_blank_webhook_url_is_worded_as_a_blank_one(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    # The final "y" accepts continuing without a URL, which is what the blank wording offers
    script = before_webhook_section() + ("y", "1", "y") + after_webhook_section()

    terminal = ScriptedTerminal(*script, secrets=secrets_for(""))
    assert run_wizard(terminal) == 0

    values = monitor.parse_config_content((tmp_path / "psn_monitor.conf").read_text(encoding="utf-8"), "psn_monitor.conf")
    assert values["WEBHOOK_ENABLED"] is False
    assert values["WEBHOOK_ERROR_NOTIFICATION"] is False
    assert terminal.asked("Continue without the webhook URL?")
    assert "complete HTTPS webhook URL" not in capsys.readouterr().out


# Verifies a code PSN keeps rejecting can be given up on, since it cannot be corrected from inside the loop
def test_a_rejected_npsso_code_can_be_abandoned(tmp_path, monkeypatch):
    def validator(code):
        raise monitor.RecoveryError(monitor.classify_recovery_error(context="secret.entry", detail="PSN rejected that code"))

    monkeypatch.setattr(monitor, "validate_npsso_code", validator)
    # The extra "n" declines entering the rejected code again
    script = happy_path()[:4] + ("n",) + happy_path()[4:]

    assert run_wizard(ScriptedTerminal(*script)) == 0

    assert "PSN_NPSSO" not in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies an abandoned mail server answer switches email off rather than writing half a configuration
def test_an_abandoned_mail_server_answer_turns_email_off(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "GAME_CHANGE_NOTIFICATION", True)
    # Cleared so the prompt has no default to fall back on, which is what a first-time setup looks like
    monkeypatch.setattr(monitor, "SMTP_HOST", "")
    # A blank SMTP host, then declining to enter it again, then declining webhooks
    script = (USER_ID, "", "", "", "y", "", "n", "n") + after_webhook_section()

    assert run_wizard(ScriptedTerminal(*script)) == 0

    values = monitor.parse_config_content((tmp_path / "psn_monitor.conf").read_text(encoding="utf-8"), "psn_monitor.conf")
    assert values["ERROR_NOTIFICATION"] is False
    assert values["GAME_CHANGE_NOTIFICATION"] is False
    assert "Email notifications stay off" in capsys.readouterr().out


# Verifies a token pasted with its authorization scheme can be given up on without losing the topic already entered
def test_a_pasted_ntfy_authorization_scheme_can_be_abandoned(tmp_path):
    # The "n" declines entering the token again, leaving the topic URL that was already accepted
    script = before_webhook_section() + ("y", "2", "y", "n", "1") + after_webhook_section()

    assert run_wizard(ScriptedTerminal(*script, secrets=lambda prompt: NPSSO if "NPSSO" in prompt else ("Bearer tk_a_real_looking_token" if "token" in prompt.casefold() else ("private-topic" if "topic" in prompt.casefold() else SMTP_SECRET)))) == 0

    env = (tmp_path / ".env").read_text(encoding="utf-8")
    assert 'WEBHOOK_URL="https://ntfy.sh/private-topic"' in env
    assert "NTFY_ACCESS_TOKEN" not in env


# The mail server answers the wizard asks for before the hidden password prompt
EMAIL_ANSWERS = ("smtp.example.test", "587", "y", "monitor@example.test", "monitor@example.test", "alerts@example.test")


# Verifies the wizard signs in with exactly the answers just given, so a wrong password is caught during setup
def test_the_wizard_signs_in_with_the_collected_mail_server(monkeypatch, capsys):
    attempts = []
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: attempts.append((values, password)) or None)

    assert run_wizard(ScriptedTerminal(*happy_path())) == 0

    assert len(attempts) == 1
    values, password = attempts[0]
    assert values == {"SMTP_HOST": "smtp.example.test", "SMTP_PORT": 587, "SMTP_SSL": True, "SMTP_USER": "monitor@example.test", "SENDER_EMAIL": "monitor@example.test", "RECEIVER_EMAIL": "alerts@example.test"}
    assert password == SMTP_SECRET
    assert "The mail server accepted the sign-in. No email was sent." in capsys.readouterr().out


# Verifies a refused sign-in offers the mail server questions again rather than saving settings that cannot work
def test_a_refused_mail_server_sign_in_offers_another_attempt(monkeypatch, capsys):
    advice = monitor.make_recovery_advice("smtp.authentication", "The mail server rejected the sign-in", "Use an app password", False, "535 authentication failed")
    results = [advice, None]
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: results.pop(0))
    answers = list(happy_path())
    terminal = ScriptedTerminal(*answers[:5], *EMAIL_ANSWERS, "y", *EMAIL_ANSWERS, *answers[11:])

    assert run_wizard(terminal) == 0

    output = capsys.readouterr().out
    assert "The mail server rejected the sign-in: 535 authentication failed" in output
    assert "To fix: Use an app password" in output
    assert terminal.asked("Try entering the mail server settings again?")
    assert not results


# Verifies declining the retry keeps the answers, since being offline is the usual reason a correct setup fails here
def test_declining_the_sign_in_retry_keeps_the_mail_server_settings(tmp_path, monkeypatch, capsys):
    advice = monitor.make_recovery_advice("smtp.connection", "The SMTP server could not be reached", "Check SMTP_HOST", True)
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: advice)
    answers = list(happy_path())
    terminal = ScriptedTerminal(*answers[:11], "n", *answers[11:])

    assert run_wizard(terminal) == 0

    assert "The settings were kept without being checked. Run --doctor to check the sign-in again." in capsys.readouterr().out
    values = monitor.parse_config_content((tmp_path / "psn_monitor.conf").read_text(encoding="utf-8"), "psn_monitor.conf")
    assert values["SMTP_HOST"] == "smtp.example.test"
    assert values["SMTP_USER"] == "monitor@example.test"


# Verifies giving up on a refused sign-in switches every email alert off rather than saving settings that cannot work
def test_abandoning_a_refused_sign_in_switches_email_off(tmp_path, monkeypatch, capsys):
    advice = monitor.make_recovery_advice("smtp.authentication", "The mail server rejected the sign-in", "Use an app password", False, "535 authentication failed")
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: advice)
    answers = list(happy_path())
    terminal = ScriptedTerminal(*answers[:11], "n", *answers[12:])

    assert run_wizard(terminal) == 0

    assert "Email notifications stay off until the mail server accepts the settings." in capsys.readouterr().out
    values = monitor.parse_config_content((tmp_path / "psn_monitor.conf").read_text(encoding="utf-8"), "psn_monitor.conf")
    assert all(values[name] is False for name in monitor.WIZARD_EMAIL_NOTIFICATION_KEYS)


# Verifies Ctrl+C at the welcome offer reports one line instead of a traceback
def test_interrupting_the_welcome_offer_reports_a_cancellation(monkeypatch, capsys):
    def interrupt(_prompt):
        raise KeyboardInterrupt

    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **_kwargs: pytest.fail("the wizard ran after being interrupted"))

    assert monitor.print_welcome_screen(interactive=True, input_func=interrupt) == 1
    assert "Setup cancelled." in capsys.readouterr().out


# Verifies an interrupt before the save says the destination files are untouched
def test_interrupting_the_questions_reports_untouched_files(tmp_path, capsys):
    exit_code = run_wizard(InterruptedTerminal())

    assert exit_code == 1
    assert "Setup cancelled. Destination files were not changed." in capsys.readouterr().out
    assert not (tmp_path / "psn_monitor.conf").exists()


# Verifies an interrupt at the doctor offer reports the saved setup instead of a cancellation
def test_interrupting_the_doctor_offer_keeps_the_saved_setup(tmp_path, capsys):
    exit_code = run_wizard(InterruptedTerminal(*happy_path()[:-2]))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Setup is saved. Use the commands below when ready." in output
    assert "Setup cancelled" not in output
    assert "Next steps" in output
    assert (tmp_path / "psn_monitor.conf").is_file()


# Verifies an interrupt at the launch offer reports the saved setup and points at the printed command
def test_interrupting_the_launch_offer_keeps_the_saved_setup(tmp_path, capsys):
    exit_code = run_wizard(InterruptedTerminal(*happy_path()[:-1]))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Setup is saved. Start monitoring with the command above when ready." in output
    assert "Setup cancelled" not in output
    assert (tmp_path / "psn_monitor.conf").is_file()


# Verifies a prompt runs with Python's default Ctrl+C behavior, so the signal handler cannot pre-empt it
def test_prompts_restore_the_default_interrupt_handler(monkeypatch):
    # The suite neutralizes signal.signal, so the installed handlers are recorded instead of applied
    installed = []
    monkeypatch.setattr(monitor.signal, "signal", lambda sig, handler: installed.append(handler))

    assert monitor._wizard_input("Prompt: ", input_func=lambda _prompt: "value") == "value"

    assert installed == [signal.default_int_handler, signal.getsignal(signal.SIGINT)]


# Verifies a destination that cannot be written is refused before the first question is asked
def test_an_unwritable_destination_is_refused_before_any_question(tmp_path, capsys):
    def refuse_every_question(prompt=""):
        raise AssertionError(f"Setup asked a question before checking its destinations: {prompt!r}")

    code = monitor.run_setup_wizard(config_file="/psn_monitor_unwritable_root.conf", env_file=str(tmp_path / ".env"), input_func=refuse_every_question, interactive=True)

    out = capsys.readouterr().out
    assert code == 1
    assert "Configuration destination is not writable" in out
    assert "To fix:" in out


# Verifies a directory given as a destination is refused rather than failing at the save step
def test_a_directory_destination_is_refused(tmp_path, capsys):
    code = monitor.run_setup_wizard(config_file=str(tmp_path), env_file=str(tmp_path / ".env"), interactive=True)

    out = capsys.readouterr().out
    assert code == 1
    assert "must be a file path, not a directory" in out


# Verifies the disabled config setting is refused, since setup exists to write one
def test_a_disabled_config_destination_is_refused(tmp_path, capsys):
    code = monitor.run_setup_wizard(config_file="none", env_file=str(tmp_path / ".env"), interactive=True)

    out = capsys.readouterr().out
    assert code == 1
    assert "--setup needs a config destination" in out


# Verifies an existing config is replaced only after the user agrees, and that a backup is kept
def test_an_existing_config_is_replaced_only_after_it_is_agreed_to(wizard_environment, capsys):
    config = wizard_environment / "psn_monitor.conf"
    config.write_text("# earlier config\n", encoding="utf-8")

    code = run_wizard(ScriptedTerminal("y", *happy_path()))

    out = capsys.readouterr().out
    backups = [path for path in wizard_environment.iterdir() if path.name.startswith("psn_monitor.conf.")]
    assert code == 0
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "# earlier config\n"
    assert "Backup:" in out


# Verifies an existing config can be kept by sending the run to another path instead
def test_an_existing_config_can_be_redirected_to_another_path(wizard_environment):
    config = wizard_environment / "psn_monitor.conf"
    config.write_text("# earlier config\n", encoding="utf-8")
    elsewhere = wizard_environment / "elsewhere.conf"

    code = run_wizard(ScriptedTerminal("n", str(elsewhere), *happy_path()))

    assert code == 0
    assert config.read_text(encoding="utf-8") == "# earlier config\n"
    assert f"PSN_USER_ID = '{USER_ID}'" in elsewhere.read_text(encoding="utf-8")


# Verifies declining to replace an existing config and naming no alternative ends the run without writing
def test_declining_an_existing_config_without_an_alternative_writes_nothing(wizard_environment, capsys):
    config = wizard_environment / "psn_monitor.conf"
    config.write_text("# earlier config\n", encoding="utf-8")

    code = run_wizard(ScriptedTerminal("n", ""))

    out = capsys.readouterr().out
    assert code == 1
    assert config.read_text(encoding="utf-8") == "# earlier config\n"
    assert not (wizard_environment / ".env").exists()
    assert "Setup cancelled. Destination files were not changed." in out


# Returns the happy-path answers with one extra answer for the dotenv replace prompt after the SMTP password
def answers_with_smtp_replace(replace):
    answers = list(happy_path())
    answers.insert(11, replace)
    return answers


# Verifies a secret already in the dotenv file is kept when the replacement is declined
def test_an_existing_dotenv_secret_is_kept_unless_the_replacement_is_confirmed(wizard_environment):
    env_file = wizard_environment / ".env"
    env_file.write_text('SMTP_PASSWORD="original"\n', encoding="utf-8")

    terminal = ScriptedTerminal(*answers_with_smtp_replace("n"))
    code = run_wizard(terminal)

    written = env_file.read_text(encoding="utf-8")
    assert code == 0
    assert terminal.asked("The dotenv file already contains SMTP_PASSWORD. Replace that value?")
    assert 'SMTP_PASSWORD="original"' in written
    assert SMTP_SECRET not in written


# Verifies a confirmed replacement does reach the dotenv file
def test_a_confirmed_dotenv_secret_replacement_is_written(wizard_environment):
    env_file = wizard_environment / ".env"
    env_file.write_text('SMTP_PASSWORD="original"\n', encoding="utf-8")

    code = run_wizard(ScriptedTerminal(*answers_with_smtp_replace("y")))

    assert code == 0
    assert f'SMTP_PASSWORD="{SMTP_SECRET}"' in env_file.read_text(encoding="utf-8")


# Verifies hidden prompts are colorized like the visible ones, so one question does not look different
def test_hidden_prompts_are_colorized_like_the_visible_ones(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)})
    prompts = []

    assert monitor._wizard_ask_secret("NPSSO code", getpass_func=lambda prompt: prompts.append(prompt) or "secret") == "secret"
    assert monitor._wizard_input("Receiver email: ", input_func=lambda prompt: prompts.append(prompt) or "") == ""

    hidden_prompt, visible_prompt = prompts
    assert hidden_prompt == monitor.colorize("info", "NPSSO code: ")
    assert hidden_prompt.startswith(visible_prompt[:visible_prompt.index("R")])
    assert hidden_prompt.endswith(monitor.ANSI_RESET)


# Verifies debug output is off while a hidden wizard answer is read and restored afterwards
def test_a_hidden_wizard_answer_is_read_with_debug_output_off(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    seen = []

    answer = monitor._wizard_ask_secret("NPSSO code", getpass_func=lambda prompt: seen.append(monitor.DEBUG_MODE) or "secret")

    assert answer == "secret"
    assert seen == [False]
    assert monitor.DEBUG_MODE is True


# Verifies the destination block states the raw install method key in the column the siblings print
def test_the_setup_header_uses_the_shared_destination_column(capsys):
    monitor._wizard_print_setup_destinations("psn_monitor.conf", ".env")

    assert capsys.readouterr().out == f"Detected install method: {monitor.detect_install_method()}\nConfiguration:          psn_monitor.conf\nDotenv:                 .env\n\n"


# Verifies the credential guidance opens its own group without the bullet the one-shot commands use
def test_the_credential_guidance_opens_its_own_group(capsys):
    run_wizard(InterruptedTerminal(USER_ID, "", "", "", secrets=lambda prompt: ""))

    transcript = capsys.readouterr().out
    assert f"\n\nSign in at https://my.playstation.com then copy the npsso value from: {monitor.NPSSO_SOURCE_URL}\n" in transcript
    assert "* Sign in at" not in transcript

# Verifies the guide link opens the setup page the sibling monitors link, with no section fragment
def test_the_welcome_guide_link_opens_the_shared_setup_page():
    assert monitor.QUICK_START_GUIDE_URL.endswith("/setup-and-first-run/")


# Verifies the doctor setup runs reports the source a restart would report, not the fallback label
def test_saved_secrets_are_credited_to_the_dotenv_file(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(f"PSN_NPSSO={NPSSO}\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
    monkeypatch.setattr(monitor, "PSN_NPSSO", "")
    state = types.SimpleNamespace(config_values={}, secret_updates={"PSN_NPSSO": NPSSO})

    monitor._wizard_apply_saved_values(state, env_path=env_path)

    assert monitor.SECRET_SOURCES["PSN_NPSSO"] == "dotenv file"
    assert "PSN_NPSSO" in monitor.doctor_secret_sources()["dotenv file"]


# Verifies an exported secret keeps its own source after setup, since the export still wins at the next start
def test_an_exported_secret_is_not_credited_to_the_dotenv_file(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(f"PSN_NPSSO={NPSSO}\n", encoding="utf-8")
    monkeypatch.setenv("PSN_NPSSO", NPSSO)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
    monkeypatch.setattr(monitor, "EXPORTED_SECRET_KEYS", {"PSN_NPSSO"})
    state = types.SimpleNamespace(config_values={}, secret_updates={})

    monitor._wizard_apply_saved_values(state, env_path=env_path)

    assert monitor.SECRET_SOURCES["PSN_NPSSO"] == "environment"


# Verifies an Auto zone in the saved config is resolved before doctor reads it, as it is on a normal start
def test_the_saved_timezone_is_resolved_before_doctor_reads_it(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "Europe/Warsaw")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE_STATE", "config")
    monkeypatch.setattr(monitor, "get_localzone", lambda: "Europe/Warsaw")
    state = types.SimpleNamespace(config_values={"LOCAL_TIMEZONE": "Auto"}, secret_updates={})

    advice = monitor._wizard_apply_saved_values(state, env_path=None)

    assert advice is None
    assert monitor.LOCAL_TIMEZONE == "Europe/Warsaw"
    assert monitor.TIMEZONE_CHECK_LABELS[monitor.LOCAL_TIMEZONE_STATE] == "Local timezone can be detected"
