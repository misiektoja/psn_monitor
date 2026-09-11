"""Tests for command line handling, startup validation and how settings reach the monitor."""

import pytest


USER_ID = "misiektoja"
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"


@pytest.fixture(autouse=True)
# Keeps generated files, the state file and the log inside the test directory
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
# Keeps startup offline and away from any config or dotenv file the developer happens to have
def isolated_startup(monkeypatch, pm_module):
    monkeypatch.setattr(pm_module, "DEFAULT_CONFIG_FILENAME", "psn_monitor_test_only.conf")
    monkeypatch.setattr(pm_module, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "none")
    monkeypatch.setattr(pm_module, "check_internet", lambda *args, **kwargs: True)


@pytest.fixture
# Replaces the monitoring loop with a recorder so main() returns after startup
def monitor_calls(monkeypatch, pm_module):
    recorded = []

    # Records the arguments the monitoring loop was started with
    def fake_monitor(psn_user_id, csv_file_name):
        recorded.append({"psn_user_id": psn_user_id, "csv_file_name": csv_file_name})

    monkeypatch.setattr(pm_module, "psn_monitor_user", fake_monitor)
    return recorded


# Runs main() with the supplied command line and returns the exit code it raised
def run_main(pm_module, monkeypatch, argv):
    monkeypatch.setattr(pm_module.sys, "argv", ["psn_monitor", *argv])
    with pytest.raises(SystemExit) as raised:
        pm_module.main()
    return raised.value.code


# Verifies the version is printed without needing credentials or a network connection
def test_version_is_printed_and_exits(pm_module, monkeypatch, capsys):
    assert run_main(pm_module, monkeypatch, ["--version"]) == 0
    assert pm_module.VERSION in capsys.readouterr().out


# Verifies running without arguments shows the help text and fails, instead of silently doing nothing
def test_bare_invocation_shows_the_welcome_screen(pm_module, monkeypatch, capsys):
    assert run_main(pm_module, monkeypatch, []) == 1

    output = capsys.readouterr().out
    # Three commands a newcomer can act on, each on its own indented line, then the two aligned footers
    assert "For <psn_user_id>, use the" in output
    assert "Quickest start (already configured):" in output
    assert "Check setup before monitoring:" in output
    assert "Show profile details and exit:" in output
    assert "Full options: " in output
    assert f"Guide:        {pm_module.QUICK_START_GUIDE_URL}" in output


# Verifies the generated config template is complete and is accepted by the tool's own parser
def test_generated_config_is_written_and_valid(pm_module, monkeypatch, isolated_working_directory):
    target = isolated_working_directory / "psn_monitor.conf"

    assert run_main(pm_module, monkeypatch, ["--generate-config", str(target)]) == 0

    content = target.read_text(encoding="utf-8")
    assert "PSN_NPSSO" in content
    assert "SMTP_HOST" in content
    pm_module.validate_config_content(content, str(target))


# Verifies the template is printed when no output file is given, so it can be redirected
def test_generated_config_is_printed_without_a_filename(pm_module, monkeypatch, capfd):
    assert run_main(pm_module, monkeypatch, ["--generate-config"]) == 0
    assert "PSN_NPSSO" in capfd.readouterr().out


# Verifies a config file supplied on the command line is applied to the run
def test_config_file_settings_reach_the_monitor(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    config = isolated_working_directory / "custom.conf"
    config.write_text('PSN_NPSSO = "npsso-from-config"\nPSN_CHECK_INTERVAL = 300\nPSN_ACTIVE_CHECK_INTERVAL = 45\n', encoding="utf-8")

    assert run_main(pm_module, monkeypatch, ["--config-file", str(config), USER_ID]) == 0

    assert pm_module.PSN_NPSSO == "npsso-from-config"
    assert pm_module.PSN_CHECK_INTERVAL == 300
    assert pm_module.PSN_ACTIVE_CHECK_INTERVAL == 45
    assert monitor_calls[0]["psn_user_id"] == USER_ID


# Verifies a config path that does not exist is refused instead of being silently ignored
def test_missing_config_file_is_refused(pm_module, monkeypatch, capsys, isolated_working_directory):
    missing = isolated_working_directory / "absent.conf"

    assert run_main(pm_module, monkeypatch, ["--config-file", str(missing), USER_ID]) == 1
    assert "does not exist" in capsys.readouterr().out


# Verifies a config file carrying executable content stops startup rather than running it
def test_executable_config_content_stops_startup(pm_module, monkeypatch, capsys, isolated_working_directory):
    hostile = isolated_working_directory / "hostile.conf"
    hostile.write_text("import os\nos.environ['PSN_CLI_EXEC_PROBE'] = 'yes'\n", encoding="utf-8")
    monkeypatch.delenv("PSN_CLI_EXEC_PROBE", raising=False)

    assert run_main(pm_module, monkeypatch, ["--config-file", str(hostile), USER_ID]) == 1

    import os

    assert os.environ.get("PSN_CLI_EXEC_PROBE") is None
    assert "read as data" in capsys.readouterr().out


# Verifies the NPSSO is picked up from a dotenv file, so it never has to be typed on the command line
def test_npsso_is_read_from_a_dotenv_file(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    pytest.importorskip("dotenv")
    env_file = isolated_working_directory / "secrets.env"
    env_file.write_text("PSN_NPSSO=npsso-from-dotenv\n", encoding="utf-8")
    monkeypatch.delenv("PSN_NPSSO", raising=False)

    assert run_main(pm_module, monkeypatch, ["--env-file", str(env_file), USER_ID]) == 0

    assert pm_module.PSN_NPSSO == "npsso-from-dotenv"


# Verifies an exported secret wins over the dotenv file, so a one-off or injected value is not silently shadowed
def test_exported_secret_overrides_the_dotenv_file(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    pytest.importorskip("dotenv")
    env_file = isolated_working_directory / "secrets.env"
    env_file.write_text("PSN_NPSSO=npsso-from-dotenv\n", encoding="utf-8")
    monkeypatch.setenv("PSN_NPSSO", "npsso-from-the-environment")

    assert run_main(pm_module, monkeypatch, ["--env-file", str(env_file), USER_ID]) == 0

    assert pm_module.PSN_NPSSO == "npsso-from-the-environment"


# Verifies an empty export is treated as absent, so a shell-profile leftover does not blank the dotenv value
def test_an_empty_export_does_not_shadow_the_dotenv_file(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    pytest.importorskip("dotenv")
    env_file = isolated_working_directory / "secrets.env"
    env_file.write_text("PSN_NPSSO=npsso-from-dotenv\n", encoding="utf-8")
    monkeypatch.setenv("PSN_NPSSO", "")

    assert run_main(pm_module, monkeypatch, ["--env-file", str(env_file), USER_ID]) == 0

    assert pm_module.PSN_NPSSO == "npsso-from-dotenv"


# Verifies an exported secret applies with no dotenv file at all, since it is a documented alternative to one
def test_exported_secret_applies_without_any_dotenv_file(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "your_psn_npsso_code")
    monkeypatch.setenv("PSN_NPSSO", "npsso-from-the-environment")

    assert run_main(pm_module, monkeypatch, ["--env-file", "none", USER_ID]) == 0

    assert pm_module.PSN_NPSSO == "npsso-from-the-environment"


# Verifies a dotenv path that does not exist is reported but does not stop a run that has a token already
def test_missing_dotenv_file_is_reported(pm_module, monkeypatch, monitor_calls, capsys, isolated_working_directory):
    pytest.importorskip("dotenv")
    missing = isolated_working_directory / "absent.env"

    assert run_main(pm_module, monkeypatch, ["--env-file", str(missing), USER_ID]) == 0
    assert "does not exist" in capsys.readouterr().out


# Verifies the command line token wins over everything else, which is what makes a one-off run possible
def test_command_line_npsso_wins(pm_module, monkeypatch, monitor_calls):
    assert run_main(pm_module, monkeypatch, ["-n", "npsso-from-cli", USER_ID]) == 0

    assert pm_module.PSN_NPSSO == "npsso-from-cli"


# Verifies startup refuses to run with the placeholder token from the template
def test_placeholder_npsso_is_refused(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "your_psn_npsso_code")

    assert run_main(pm_module, monkeypatch, [USER_ID]) == 1
    assert "PSN_NPSSO (-n / --npsso_key) value is empty or incorrect" in capsys.readouterr().out


# Verifies a run without a user to watch is refused with an explanation
def test_missing_user_id_is_refused(pm_module, monkeypatch, capsys):
    assert run_main(pm_module, monkeypatch, ["-n", "npsso-from-cli"]) == 1
    assert "PSN_USER_ID needs to be defined" in capsys.readouterr().out


# Verifies an unusable timezone is caught at startup instead of surfacing on the first timestamp
def test_invalid_timezone_is_refused(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "LOCAL_TIMEZONE", "Mars/Olympus_Mons")

    assert run_main(pm_module, monkeypatch, [USER_ID]) == 1
    assert "is not valid" in capsys.readouterr().out


# Verifies a misspelled separator mode is caught at startup rather than on the first log line
def test_invalid_separator_mode_is_refused(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "ASCII_LOG_SEPARATORS", "yes please")

    assert run_main(pm_module, monkeypatch, [USER_ID]) == 1
    assert "ASCII_LOG_SEPARATORS must be" in capsys.readouterr().out


# Verifies a missing internet connection stops startup, since every poll would fail anyway
def test_missing_connectivity_stops_startup(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "check_internet", lambda *args, **kwargs: False)

    assert run_main(pm_module, monkeypatch, [USER_ID]) == 1


# Verifies a CSV path that cannot be written is caught before monitoring starts
def test_unwritable_csv_path_is_refused(pm_module, monkeypatch, capsys, isolated_working_directory):
    unreachable = isolated_working_directory / "missing-directory" / "history.csv"

    assert run_main(pm_module, monkeypatch, ["-b", str(unreachable), USER_ID]) == 1
    assert "cannot be opened for writing" in capsys.readouterr().out


# Verifies the CSV path reaches the monitoring loop with the user's home directory expanded
def test_csv_path_reaches_the_monitor(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    history = isolated_working_directory / "history.csv"

    assert run_main(pm_module, monkeypatch, ["-b", str(history), USER_ID]) == 0

    assert monitor_calls[0]["csv_file_name"] == str(history)


# Verifies the interval flags override the configured polling intervals
def test_interval_flags_override_the_configuration(pm_module, monkeypatch, monitor_calls):
    assert run_main(pm_module, monkeypatch, ["-c", "600", "-k", "30", USER_ID]) == 0

    assert pm_module.PSN_CHECK_INTERVAL == 600
    assert pm_module.PSN_ACTIVE_CHECK_INTERVAL == 30
    assert pm_module.LIVENESS_REMINDER_SECONDS == pm_module.LIVENESS_CHECK_INTERVAL


# Verifies a check interval longer than the liveness interval leaves the configured reminder alone
def test_a_long_check_interval_keeps_the_configured_liveness_interval(pm_module, monkeypatch, monitor_calls):
    assert run_main(pm_module, monkeypatch, ["-c", "86400", USER_ID]) == 0

    assert pm_module.LIVENESS_REMINDER_SECONDS == pm_module.LIVENESS_CHECK_INTERVAL


# Verifies a liveness interval set in a config file reaches the loop, without --check-interval on the same run
def test_a_configured_liveness_interval_reaches_the_loop_on_its_own(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    config = isolated_working_directory / "liveness.conf"
    config.write_text('PSN_NPSSO = "npsso-from-config"\nLIVENESS_CHECK_INTERVAL = 900\n', encoding="utf-8")

    assert run_main(pm_module, monkeypatch, ["--config-file", str(config), USER_ID]) == 0

    assert pm_module.LIVENESS_CHECK_INTERVAL == 900
    assert pm_module.LIVENESS_REMINDER_SECONDS == 900


# Verifies a liveness interval switched off in a config file reaches the loop as a disabled reminder
def test_a_disabled_liveness_reminder_reaches_the_loop(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    config = isolated_working_directory / "quiet.conf"
    config.write_text('PSN_NPSSO = "npsso-from-config"\nLIVENESS_CHECK_INTERVAL = 0\n', encoding="utf-8")

    assert run_main(pm_module, monkeypatch, ["--config-file", str(config), USER_ID]) == 0

    assert pm_module.LIVENESS_REMINDER_SECONDS == 0


# Verifies the notification flags switch on exactly the alerts they name
def test_notification_flags_switch_on_the_named_alerts(pm_module, monkeypatch, monitor_calls):
    assert run_main(pm_module, monkeypatch, ["-a", "-g", USER_ID]) == 0

    assert pm_module.ACTIVE_INACTIVE_NOTIFICATION is True
    assert pm_module.GAME_CHANGE_NOTIFICATION is True
    assert pm_module.ERROR_NOTIFICATION is False


# Verifies error alerts can be switched off from the command line
def test_error_alerts_can_be_disabled(pm_module, monkeypatch, monitor_calls):
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)

    assert run_main(pm_module, monkeypatch, ["-e", USER_ID]) == 0

    assert pm_module.ERROR_NOTIFICATION is False


# Verifies notifications are switched off when SMTP was never configured, so nothing fails on every change
def test_unconfigured_smtp_disables_every_notification(pm_module, monkeypatch, monitor_calls, capsys):
    monkeypatch.setattr(pm_module, "SMTP_HOST", "your_smtp_server_ssl")
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)

    assert run_main(pm_module, monkeypatch, ["-a", "-g", USER_ID]) == 0

    assert pm_module.ACTIVE_INACTIVE_NOTIFICATION is False
    assert pm_module.GAME_CHANGE_NOTIFICATION is False
    assert pm_module.ERROR_NOTIFICATION is False


# Verifies the startup banner reports the settings the run will actually use
def test_startup_banner_reports_the_effective_settings(pm_module, monkeypatch, monitor_calls, capsys):
    assert run_main(pm_module, monkeypatch, ["-c", "600", "-k", "30", USER_ID]) == 0

    output = capsys.readouterr().out
    assert "* Polling intervals:" in output
    assert "[offline: 10 minutes] [online: 30 seconds]" in output
    assert f"Monitoring user with PSN ID {USER_ID}" in output
    # The time zone is a full-view row, so the concise banner leaves it out
    assert "Local timezone:" not in output


# Verifies the log file is created next to the working directory and named after the monitored user
def test_log_file_is_named_after_the_user(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    monkeypatch.setattr(pm_module, "DISABLE_LOGGING", False)
    monkeypatch.setattr(pm_module, "PSN_LOGFILE", "psn_monitor")

    assert run_main(pm_module, monkeypatch, [USER_ID]) == 0

    log_file = isolated_working_directory / f"psn_monitor_{USER_ID}.log"
    assert log_file.is_file()
    assert "Monitoring user with PSN ID" in log_file.read_text(encoding="utf-8")


# Verifies logging can be switched off, which a container or systemd deployment relies on
def test_logging_can_be_disabled(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    monkeypatch.setattr(pm_module, "DISABLE_LOGGING", False)
    monkeypatch.setattr(pm_module, "PSN_LOGFILE", "psn_monitor")

    assert run_main(pm_module, monkeypatch, ["-d", USER_ID]) == 0

    assert not (isolated_working_directory / f"psn_monitor_{USER_ID}.log").exists()


# Verifies the test email uses the configured SMTP settings and reports the outcome
def test_test_email_reports_success(pm_module, monkeypatch, sent_emails, capsys):
    assert run_main(pm_module, monkeypatch, ["--send-test-email"]) == 0

    assert len(sent_emails) == 1
    assert sent_emails[0]["subject"] == "psn_monitor: test email"
    assert "Email sent successfully" in capsys.readouterr().out


# Verifies a failing test email exits with an error, so a broken relay is noticed immediately
def test_failing_test_email_exits_with_an_error(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "send_email", lambda *args, **kwargs: 1)

    assert run_main(pm_module, monkeypatch, ["--send-test-email"]) == 1


# Verifies the reporting mode runs once with the requested sections and never enters the monitoring loop
def test_info_mode_runs_once_with_the_requested_sections(pm_module, monkeypatch, monitor_calls):
    recorded = {}

    # Records how the reporting mode was invoked
    def fake_info(psn_user_id, include_trophies=False, show_recent_games=True):
        recorded.update({"psn_user_id": psn_user_id, "include_trophies": include_trophies, "show_recent_games": show_recent_games})

    monkeypatch.setattr(pm_module, "get_user_info", fake_info)

    assert run_main(pm_module, monkeypatch, ["-i", "--trophies", "--no-recent-games", USER_ID]) == 0

    assert recorded == {"psn_user_id": USER_ID, "include_trophies": True, "show_recent_games": False}
    assert monitor_calls == []


# Verifies the reporting mode defaults to recently played games and no trophy section
def test_info_mode_defaults(pm_module, monkeypatch, monitor_calls):
    recorded = {}

    # Records how the reporting mode was invoked
    def fake_info(psn_user_id, include_trophies=False, show_recent_games=True):
        recorded.update({"include_trophies": include_trophies, "show_recent_games": show_recent_games})

    monkeypatch.setattr(pm_module, "get_user_info", fake_info)

    assert run_main(pm_module, monkeypatch, ["-i", USER_ID]) == 0

    assert recorded == {"include_trophies": False, "show_recent_games": True}


# Verifies an optional config file in the working directory is picked up without a flag
def test_config_file_in_the_working_directory_is_used(pm_module, monkeypatch, monitor_calls, isolated_working_directory, capsys):
    config = isolated_working_directory / "psn_monitor_test_only.conf"
    config.write_text("PSN_CHECK_INTERVAL = 900\n", encoding="utf-8")

    assert run_main(pm_module, monkeypatch, [USER_ID]) == 0

    assert pm_module.PSN_CHECK_INTERVAL == 900
    output = capsys.readouterr().out
    assert "* Config:" in output
    assert str(config) in output


# Verifies the source of an exported secret is recorded, which is what makes a stale export visible later
def test_exported_secret_source_is_recorded(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    pytest.importorskip("dotenv")
    env_file = isolated_working_directory / "secrets.env"
    env_file.write_text("PSN_NPSSO=npsso-from-dotenv\n", encoding="utf-8")
    monkeypatch.setenv("PSN_NPSSO", "npsso-from-the-environment")

    assert run_main(pm_module, monkeypatch, ["--env-file", str(env_file), USER_ID]) == 0

    assert pm_module.SECRET_SOURCES["PSN_NPSSO"] == "environment"


# Verifies a secret supplied only by the dotenv file is credited to the file rather than to the environment
def test_dotenv_secret_source_is_recorded(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    pytest.importorskip("dotenv")
    env_file = isolated_working_directory / "secrets.env"
    env_file.write_text("PSN_NPSSO=npsso-from-dotenv\n", encoding="utf-8")
    monkeypatch.delenv("PSN_NPSSO", raising=False)

    assert run_main(pm_module, monkeypatch, ["--env-file", str(env_file), USER_ID]) == 0

    assert pm_module.SECRET_SOURCES["PSN_NPSSO"] == "dotenv file"


# Verifies a secret that came from the config file is recorded as such
def test_config_file_secret_source_is_recorded(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    config = isolated_working_directory / "custom.conf"
    config.write_text('PSN_NPSSO = "npsso-from-config"\n', encoding="utf-8")

    assert run_main(pm_module, monkeypatch, ["--config-file", str(config), "--env-file", "none", USER_ID]) == 0

    assert pm_module.SECRET_SOURCES["PSN_NPSSO"] == "configuration file"


# Verifies the command line is recorded as the winning source, since it overrides every other one
def test_command_line_secret_source_is_recorded(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    pytest.importorskip("dotenv")
    env_file = isolated_working_directory / "secrets.env"
    env_file.write_text("PSN_NPSSO=npsso-from-dotenv\n", encoding="utf-8")

    assert run_main(pm_module, monkeypatch, ["--env-file", str(env_file), "-n", "npsso-from-cli", USER_ID]) == 0

    assert pm_module.SECRET_SOURCES["PSN_NPSSO"] == "command line"


# Verifies the screen truncation width from the command line reaches the writer that applies it
def test_truncation_width_from_the_command_line_reaches_the_writer(pm_module, monkeypatch, monitor_calls):
    monkeypatch.setattr(pm_module, "DISABLE_LOGGING", False)

    assert run_main(pm_module, monkeypatch, ["--truncate", "100", USER_ID]) == 0

    assert pm_module.TRUNCATE_CHARS == 100


# Verifies a PSN ID saved in the config file starts monitoring instead of showing the welcome screen
def test_a_saved_psn_user_id_is_used_when_none_is_given(pm_module, monkeypatch, monitor_calls, isolated_working_directory, capsys):
    config = isolated_working_directory / "psn_monitor_test_only.conf"
    config.write_text(f'PSN_USER_ID = "{USER_ID}"\n', encoding="utf-8")

    assert run_main(pm_module, monkeypatch, []) == 0

    assert monitor_calls[0]["psn_user_id"] == USER_ID
    assert "Quickest start" not in capsys.readouterr().out


# Verifies a PSN ID typed on the command line wins over the saved one
def test_a_given_psn_user_id_wins_over_the_saved_one(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    config = isolated_working_directory / "psn_monitor_test_only.conf"
    config.write_text('PSN_USER_ID = "saved_player"\n', encoding="utf-8")

    assert run_main(pm_module, monkeypatch, [USER_ID]) == 0

    assert monitor_calls[0]["psn_user_id"] == USER_ID


# Verifies a config file that saves no PSN ID still leaves a bare run at the welcome screen
def test_a_config_without_a_saved_id_still_shows_the_welcome_screen(pm_module, monkeypatch, isolated_working_directory, capsys):
    config = isolated_working_directory / "psn_monitor_test_only.conf"
    config.write_text("PSN_CHECK_INTERVAL = 900\n", encoding="utf-8")

    assert run_main(pm_module, monkeypatch, []) == 1

    assert "Quickest start" in capsys.readouterr().out


# Verifies the status file destination from the command line reaches the file the monitor saves to
def test_the_status_file_from_the_command_line_reaches_the_monitor(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    destination = isolated_working_directory / "history" / "last_status.json"

    assert run_main(pm_module, monkeypatch, ["--status-file", str(destination), USER_ID]) == 0

    assert pm_module.resolve_status_file(USER_ID) == str(destination)


# Verifies the status file destination from the config file reaches the same place
def test_the_status_file_from_the_config_file_reaches_the_monitor(pm_module, monkeypatch, monitor_calls, isolated_working_directory):
    config = isolated_working_directory / "psn_monitor_test_only.conf"
    config.write_text('PSN_STATUS_FILE = "saved_status.json"\n', encoding="utf-8")

    assert run_main(pm_module, monkeypatch, [USER_ID]) == 0

    assert pm_module.resolve_status_file(USER_ID).endswith("saved_status.json")


# Verifies the default status file name is still the per-user one, so an upgrade keeps its history
def test_the_default_status_file_keeps_the_existing_name(pm_module, monkeypatch, monitor_calls):
    assert run_main(pm_module, monkeypatch, [USER_ID]) == 0

    assert pm_module.resolve_status_file(USER_ID) == f"psn_{USER_ID}_last_status.json"


# Verifies a generated config is written where it was asked for
def test_generate_config_writes_the_named_file(pm_module, monkeypatch, isolated_working_directory, capsys):
    destination = isolated_working_directory / "generated.conf"

    assert run_main(pm_module, monkeypatch, ["--generate-config", str(destination)]) == 0

    assert "PSN_CHECK_INTERVAL" in destination.read_text(encoding="utf-8")
    assert f"Config written to: {destination}" in capsys.readouterr().out


# Verifies a second run cannot quietly replace the config the first one wrote
def test_generate_config_refuses_to_replace_an_existing_file(pm_module, monkeypatch, isolated_working_directory, capsys):
    destination = isolated_working_directory / "generated.conf"
    destination.write_text("PSN_CHECK_INTERVAL = 900\n", encoding="utf-8")

    assert run_main(pm_module, monkeypatch, ["--generate-config", str(destination)]) == 1

    assert destination.read_text(encoding="utf-8") == "PSN_CHECK_INTERVAL = 900\n"
    output = capsys.readouterr().out
    assert "already exists" in output
    assert "--force" in output


# Verifies --force replaces the config and says where the previous one was kept
def test_generate_config_with_force_keeps_a_backup(pm_module, monkeypatch, isolated_working_directory, capsys):
    destination = isolated_working_directory / "generated.conf"
    destination.write_text("PSN_CHECK_INTERVAL = 900\n", encoding="utf-8")

    assert run_main(pm_module, monkeypatch, ["--generate-config", str(destination), "--force"]) == 0

    assert "PSN_CHECK_INTERVAL = 900" not in destination.read_text(encoding="utf-8")
    backups = [path for path in isolated_working_directory.iterdir() if path.name.endswith(".bak")]
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "PSN_CHECK_INTERVAL = 900\n"
    assert "Previous config backed up to:" in capsys.readouterr().out


# Verifies the template still goes to standard output when no filename is given, which is the documented default
def test_generate_config_without_a_filename_prints_the_template(pm_module, monkeypatch, capsys):
    assert run_main(pm_module, monkeypatch, ["--generate-config"]) == 0

    assert "PSN_CHECK_INTERVAL" in capsys.readouterr().out


@pytest.mark.parametrize("flag", ["--set-npsso", "--set-smtp-password"])
# Verifies a one-shot secret command refuses rather than reading a secret from a pipe that anyone can log
def test_setting_a_secret_needs_a_terminal(pm_module, monkeypatch, capsys, flag):
    assert run_main(pm_module, monkeypatch, [flag]) == 1

    output = capsys.readouterr().out
    assert "interactive terminal" in output
    # The command works on its own, so it must not fail for the missing PSN ID first
    assert "No PlayStation ID was given" not in output


# Verifies the saved secret goes to the dotenv file the run was told to use
def test_setting_a_secret_writes_to_the_selected_dotenv_file(pm_module, monkeypatch, isolated_working_directory, psn_session, capsys):
    env_file = isolated_working_directory / "secrets.env"
    monkeypatch.setattr(pm_module.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(pm_module.getpass, "getpass", lambda prompt: "a-fresh-npsso-code")

    assert run_main(pm_module, monkeypatch, ["--env-file", str(env_file), "--set-npsso"]) == 0

    assert env_file.read_text(encoding="utf-8") == 'PSN_NPSSO="a-fresh-npsso-code"\n'
    assert "a-fresh-npsso-code" not in capsys.readouterr().out


# Verifies --setup reaches the wizard with the files this run was told to use
def test_setup_reaches_the_wizard_with_the_selected_files(pm_module, monkeypatch, isolated_working_directory):
    seen = []
    monkeypatch.setattr(pm_module, "run_setup_wizard", lambda **kwargs: seen.append(kwargs) or 0)

    assert run_main(pm_module, monkeypatch, ["--setup", "--config-file", "custom.conf", USER_ID]) == 0

    assert seen[0]["initial_target"] == USER_ID
    assert seen[0]["config_file"] == "custom.conf"


# Verifies a command that is about to create the dotenv file is not warned that it does not exist, since the
# path it was given is that command's destination
def test_a_command_that_writes_the_dotenv_file_is_not_warned_that_it_is_missing(pm_module, monkeypatch, isolated_working_directory, capsys):
    pytest.importorskip("dotenv")
    monkeypatch.setattr(pm_module, "run_setup_wizard", lambda **kwargs: 0)

    assert run_main(pm_module, monkeypatch, ["--setup", "--env-file", str(isolated_working_directory / "absent.env"), "--config-file", "not-created-yet.conf"]) == 0

    assert "does not exist" not in capsys.readouterr().out


# Verifies a config path that does not exist yet is setup's destination rather than a reason to stop
def test_setup_accepts_a_config_path_that_does_not_exist_yet(pm_module, monkeypatch, isolated_working_directory, capsys):
    monkeypatch.setattr(pm_module, "run_setup_wizard", lambda **kwargs: 0)

    assert run_main(pm_module, monkeypatch, ["--setup", "--config-file", "not-created-yet.conf"]) == 0

    assert "does not exist" not in capsys.readouterr().out


@pytest.fixture
# Makes the captured stream look like a colour-capable terminal so startup resolves colour on
def color_capable_terminal(monkeypatch, pm_module):
    monkeypatch.setattr(pm_module, "_stream_supports_color", lambda stream: True)
    monkeypatch.setattr(pm_module, "COLORED_OUTPUT", True)


# Verifies colour reaches the startup banner, which is printed before the arguments are parsed
def test_the_startup_banner_is_coloured(pm_module, monkeypatch, monitor_calls, capsys, color_capable_terminal):
    assert run_main(pm_module, monkeypatch, [USER_ID]) == 0

    assert f"\x1b[96m{pm_module.STARTUP_BANNER.splitlines()[1]}\x1b[0m" in capsys.readouterr().out


# Verifies a config file that switches colour off is read early enough to reach the banner. Without the early
# peek the banner would already be coloured by the time the config file is loaded
def test_a_config_that_disables_colour_is_read_before_the_banner(pm_module, monkeypatch, monitor_calls, capsys, color_capable_terminal, isolated_working_directory):
    (isolated_working_directory / "psn_monitor_test_only.conf").write_text("CLEAR_SCREEN = False\nCOLORED_OUTPUT = False\n", encoding="utf-8")

    assert run_main(pm_module, monkeypatch, [USER_ID]) == 0

    assert "\x1b" not in capsys.readouterr().out
    assert pm_module.COLOR_ENABLED is False


# Verifies --no-color is honoured from the raw command line, so even the banner printed before argparse is plain
def test_the_no_color_flag_reaches_the_banner(pm_module, monkeypatch, monitor_calls, capsys, color_capable_terminal):
    assert run_main(pm_module, monkeypatch, ["--no-color", USER_ID]) == 0

    assert "\x1b" not in capsys.readouterr().out
    assert pm_module.COLOR_ENABLED is False


# Verifies an abbreviated --no-color still switches colour off. The raw scan before argparse only matches the
# full spelling, so this is the flag arriving through argparse instead
def test_an_abbreviated_no_color_flag_still_disables_colour(pm_module, monkeypatch, monitor_calls, color_capable_terminal):
    assert run_main(pm_module, monkeypatch, ["--no-col", USER_ID]) == 0

    assert pm_module.COLOR_ENABLED is False


# Verifies naming a destination on the command line switches the channel on for that run
def test_a_webhook_url_on_the_command_line_enables_the_channel(pm_module, monkeypatch, monitor_calls):
    assert run_main(pm_module, monkeypatch, [USER_ID, "--webhook-url", WEBHOOK_URL]) == 0

    assert pm_module.WEBHOOK_ENABLED is True
    assert pm_module.WEBHOOK_URL == WEBHOOK_URL
    assert pm_module.SECRET_SOURCES["WEBHOOK_URL"] == "command line"


# Verifies a destination that is not a complete HTTPS link is refused before monitoring starts
def test_an_unusable_webhook_url_is_refused(pm_module, monkeypatch, capsys):
    assert run_main(pm_module, monkeypatch, [USER_ID, "--webhook-url", "http://discord.com/api/webhooks/1/token"]) == 2

    assert "--webhook-url" in capsys.readouterr().err


# Verifies naming one alert is enough to switch the channel on with it
def test_naming_one_alert_enables_the_channel(pm_module, monkeypatch, monitor_calls):
    assert run_main(pm_module, monkeypatch, [USER_ID, "--webhook-url", WEBHOOK_URL, "--webhook-game-change"]) == 0

    assert pm_module.WEBHOOK_GAME_CHANGE_NOTIFICATION is True
    assert pm_module.WEBHOOK_ENABLED is True


# Verifies the explicit switch wins over the destination that would otherwise enable the channel
def test_the_off_switch_wins_over_a_supplied_destination(pm_module, monkeypatch, monitor_calls):
    assert run_main(pm_module, monkeypatch, [USER_ID, "--webhook-url", WEBHOOK_URL, "--no-webhook"]) == 0

    assert pm_module.WEBHOOK_ENABLED is False


# Verifies the error alert can be switched off on its own without disabling the channel
def test_the_webhook_error_alert_can_be_switched_off(pm_module, monkeypatch, monitor_calls):
    assert run_main(pm_module, monkeypatch, [USER_ID, "--webhook-url", WEBHOOK_URL, "--no-webhook-error-notify"]) == 0

    assert pm_module.WEBHOOK_ERROR_NOTIFICATION is False
    assert pm_module.WEBHOOK_ENABLED is True


# Verifies a recognised URL corrects a provider the settings got wrong, and says so once
def test_a_recognised_url_corrects_the_configured_provider(pm_module, monkeypatch, monitor_calls, capsys):
    monkeypatch.setattr(pm_module, "WEBHOOK_PROVIDER", "ntfy")

    assert run_main(pm_module, monkeypatch, [USER_ID, "--webhook-url", WEBHOOK_URL]) == 0

    assert pm_module.WEBHOOK_PROVIDER == "discord"
    assert "Configured webhook provider did not match the URL" in capsys.readouterr().out


# Verifies an explicitly chosen provider is left alone, even when the URL points somewhere else
def test_an_explicit_provider_is_not_corrected(pm_module, monkeypatch, monitor_calls):
    assert run_main(pm_module, monkeypatch, [USER_ID, "--webhook-url", WEBHOOK_URL, "--webhook-provider", "ntfy"]) == 0

    assert pm_module.WEBHOOK_PROVIDER == "ntfy"


# Verifies an enabled channel with an unusable destination is switched off rather than failing at each alert
def test_an_enabled_channel_without_a_destination_is_switched_off(pm_module, monkeypatch, monitor_calls):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)

    assert run_main(pm_module, monkeypatch, [USER_ID]) == 0

    assert pm_module.WEBHOOK_ENABLED is False


# Verifies the test webhook is sent past the alert settings and exits without starting monitoring
def test_the_test_webhook_is_sent_and_exits(pm_module, monkeypatch, sent_webhooks, capsys):
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", WEBHOOK_URL)

    assert run_main(pm_module, monkeypatch, [USER_ID, "--send-test-webhook"]) == 0

    assert len(sent_webhooks) == 1
    assert sent_webhooks[0]["force"] is True
    output = capsys.readouterr().out
    assert "discord.com" in output
    assert WEBHOOK_URL not in output


# Verifies a failed test webhook exits non-zero, so a setup script can act on it
def test_a_failed_test_webhook_exits_non_zero(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "send_webhook", lambda *args, **kwargs: 1)

    assert run_main(pm_module, monkeypatch, [USER_ID, "--send-test-webhook"]) == 1


# Verifies both test commands carry the subject, title and body shared with the sibling monitors
def test_the_test_messages_use_the_shared_wording(pm_module, monkeypatch, sent_emails, sent_webhooks):
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", WEBHOOK_URL)

    assert run_main(pm_module, monkeypatch, [USER_ID, "--send-test-email"]) == 0
    assert run_main(pm_module, monkeypatch, [USER_ID, "--send-test-webhook"]) == 0

    assert (sent_emails[0]["subject"], sent_emails[0]["body"]) == ("psn_monitor: test email", "This test email was sent by --send-test-email. Your SMTP settings work.")
    assert (sent_webhooks[0]["title"], sent_webhooks[0]["description"]) == ("psn_monitor: test webhook", "This test notification was sent by --send-test-webhook. Your webhook settings work.")


@pytest.mark.parametrize("flag, announcement", [("--send-test-email", "Sending test email notification"), ("--send-test-webhook", "Sending test webhook notification")])
# Verifies a delivery test checks the settings before it announces an attempt it cannot make
def test_a_delivery_test_checks_the_settings_before_it_announces(pm_module, monkeypatch, capsys, flag, announcement):
    monkeypatch.setattr(pm_module, "SMTP_HOST", "not a host")
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", "")

    assert run_main(pm_module, monkeypatch, [USER_ID, flag]) == 1

    output = capsys.readouterr().out
    assert announcement not in output
    assert "* Error: " in output
    assert "To fix: " in output


# Verifies --setup runs before the connectivity probe, since it writes files and needs no network
def test_setup_runs_before_the_connectivity_probe(pm_module, monkeypatch, isolated_working_directory):
    def refuse_probe(*args, **kwargs):
        raise AssertionError("the connectivity probe ran before setup")

    monkeypatch.setattr(pm_module, "check_internet", refuse_probe)
    monkeypatch.setattr(pm_module, "run_setup_wizard", lambda **kwargs: 0)

    assert run_main(pm_module, monkeypatch, ["--setup", "--config-file", "custom.conf"]) == 0
