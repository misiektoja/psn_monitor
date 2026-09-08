"""Tests for the guided setup: what it asks, what it writes and when it writes nothing."""

import re

import pytest

import psn_monitor as monitor


USER_ID = "misiektoja"
NPSSO = "a-fresh-npsso-code"
SMTP_SECRET = "aVeryLongSmtpPassword123"
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"


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
        "y", "", "", "y",              # keep the log, no CSV, default status file, coloured output
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
    # The extra "n" answers "Continue without a code?", which must default to keeping the setup usable
    script = happy_path()[:4] + ("n",) + happy_path()[4:]
    terminal = ScriptedTerminal(*script, secrets=lambda prompt: entered.pop(0) if "NPSSO" in prompt else SMTP_SECRET)

    run_wizard(terminal)

    assert entered == []
    assert terminal.asked("Continue without a code?")


# Verifies a code PSN rejects is asked again instead of being written
def test_a_rejected_npsso_code_is_asked_again(tmp_path, monkeypatch):
    attempts = ["bad-code", NPSSO]

    def validator(code):
        if code == "bad-code":
            raise monitor.RecoveryError(monitor.classify_recovery_error(context="secret.entry", detail="PSN rejected that code"))
        return "signed-in-account"

    monkeypatch.setattr(monitor, "validate_npsso_code", validator)

    run_wizard(ScriptedTerminal(*happy_path(), secrets=lambda prompt: attempts.pop(0) if "NPSSO" in prompt else SMTP_SECRET))

    assert attempts == []
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
    assert "Webhook notifications:" in output


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
