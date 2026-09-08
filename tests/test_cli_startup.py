"""Tests for command line handling, startup validation and how settings reach the monitor."""

import pytest


USER_ID = "misiektoja"


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
def test_bare_invocation_shows_help(pm_module, monkeypatch, capsys):
    assert run_main(pm_module, monkeypatch, []) == 1
    assert "usage: psn_monitor" in capsys.readouterr().err


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
    assert "CSV file cannot be opened for writing" in capsys.readouterr().out


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
    assert pm_module.LIVENESS_CHECK_COUNTER == pm_module.LIVENESS_CHECK_INTERVAL / 600


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
    assert "* PSN polling intervals:\t[offline: 10 minutes] [online: 30 seconds]" in output
    assert "* Local timezone:\t\tUTC" in output
    assert f"Monitoring user with PSN ID {USER_ID}" in output


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
    assert f"* Configuration file:\t\t{config}" in capsys.readouterr().out
