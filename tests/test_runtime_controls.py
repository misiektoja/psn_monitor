"""Tests for the signal-driven runtime controls and the log output filter."""

import signal

import pytest


# Verifies SIGUSR1 flips online/offline notifications without a restart
def test_status_notifications_toggle_on_sigusr1(pm_module, capsys):
    assert pm_module.ACTIVE_INACTIVE_NOTIFICATION is False

    pm_module.toggle_active_inactive_notifications_signal_handler(signal.SIGUSR1, None)
    assert pm_module.ACTIVE_INACTIVE_NOTIFICATION is True

    pm_module.toggle_active_inactive_notifications_signal_handler(signal.SIGUSR1, None)
    assert pm_module.ACTIVE_INACTIVE_NOTIFICATION is False
    assert "active/inactive status changes" in capsys.readouterr().out


# Verifies SIGUSR2 flips game change notifications without a restart
def test_game_notifications_toggle_on_sigusr2(pm_module, capsys):
    pm_module.toggle_game_change_notifications_signal_handler(signal.SIGUSR2, None)

    assert pm_module.GAME_CHANGE_NOTIFICATION is True
    assert "game changes" in capsys.readouterr().out


# Verifies SIGTRAP raises the online polling interval by the configured step
def test_active_interval_increases_on_sigtrap(pm_module):
    pm_module.increase_active_check_signal_handler(signal.SIGTRAP, None)

    assert pm_module.PSN_ACTIVE_CHECK_INTERVAL == 90


# Verifies SIGABRT lowers the online polling interval by the configured step
def test_active_interval_decreases_on_sigabrt(pm_module):
    pm_module.decrease_active_check_signal_handler(signal.SIGABRT, None)

    assert pm_module.PSN_ACTIVE_CHECK_INTERVAL == 30


# Verifies the polling interval is never driven to zero or below, which would spin the loop
def test_active_interval_never_drops_to_zero(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_ACTIVE_CHECK_INTERVAL", 30)

    pm_module.decrease_active_check_signal_handler(signal.SIGABRT, None)

    assert pm_module.PSN_ACTIVE_CHECK_INTERVAL == 30


# Verifies SIGHUP picks up a rotated NPSSO from the dotenv file without a restart
def test_sighup_reloads_rotated_secrets(pm_module, tmp_path, monkeypatch, capsys):
    pytest.importorskip("dotenv")
    env_file = tmp_path / ".env"
    env_file.write_text("PSN_NPSSO=rotated-npsso-value\nSMTP_PASSWORD=rotated-smtp-password\n", encoding="utf-8")
    monkeypatch.setattr(pm_module, "DOTENV_FILE", str(env_file))
    monkeypatch.delenv("PSN_NPSSO", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)

    pm_module.reload_secrets_signal_handler(signal.SIGHUP, None)

    try:
        assert pm_module.PSN_NPSSO == "rotated-npsso-value"
        assert pm_module.SMTP_PASSWORD == "rotated-smtp-password"
        assert "Reloaded PSN_NPSSO" in capsys.readouterr().out
    finally:
        pm_module.PSN_NPSSO = "npsso-test-value"
        pm_module.SMTP_PASSWORD = "not-a-real-password"


# Verifies a secret is never printed when it is reloaded, only its name and the file it came from
def test_reloaded_secrets_are_not_printed(pm_module, tmp_path, monkeypatch, capsys):
    pytest.importorskip("dotenv")
    env_file = tmp_path / ".env"
    env_file.write_text("PSN_NPSSO=super-secret-token-value\n", encoding="utf-8")
    monkeypatch.setattr(pm_module, "DOTENV_FILE", str(env_file))
    monkeypatch.delenv("PSN_NPSSO", raising=False)

    pm_module.reload_secrets_signal_handler(signal.SIGHUP, None)

    try:
        assert "super-secret-token-value" not in capsys.readouterr().out
    finally:
        pm_module.PSN_NPSSO = "npsso-test-value"


# Verifies the dotenv scan can be turned off entirely, which a container deployment relies on
def test_dotenv_reload_can_be_disabled(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "DOTENV_FILE", "none")
    monkeypatch.setenv("PSN_NPSSO", "value-from-the-environment")

    pm_module.reload_secrets_signal_handler(signal.SIGHUP, None)

    assert pm_module.PSN_NPSSO == "npsso-test-value"


@pytest.mark.parametrize("mode,system,expected", [
    ("Auto", "Windows", True),
    ("Auto", "Linux", False),
    ("Auto", "Darwin", False),
    ("On", "Linux", True),
    ("Off", "Windows", False),
    (" on ", "Linux", True),
])
# Verifies the ASCII separator mode resolves the way the configuration documents it
def test_ascii_separator_mode_resolution(pm_module, monkeypatch, mode, system, expected):
    monkeypatch.setattr(pm_module, "ASCII_LOG_SEPARATORS", mode)
    monkeypatch.setattr(pm_module.platform, "system", lambda: system)

    assert pm_module.ascii_log_separators_enabled() is expected


# Verifies a misspelled mode is rejected by name so startup can explain the mistake
def test_unknown_separator_mode_is_rejected(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "ASCII_LOG_SEPARATORS", "yes please")

    with pytest.raises(ValueError, match="ASCII_LOG_SEPARATORS"):
        pm_module.ascii_log_separators_enabled()


# Verifies separator lines become ASCII when enabled, so a Windows log file stays readable
def test_separator_lines_are_converted_when_enabled(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "ASCII_LOG_SEPARATORS", "On")

    assert pm_module.normalize_log_separators("─────\n") == "-----\n"


# Verifies only separator-only lines are converted, so a title containing a dash is left alone
def test_only_separator_lines_are_converted(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "ASCII_LOG_SEPARATORS", "On")

    assert pm_module.normalize_log_separators("Game: Ni no Kuni ─ Wrath\n") == "Game: Ni no Kuni ─ Wrath\n"


# Verifies the log text is untouched when the conversion is off
def test_separator_lines_are_preserved_when_disabled(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "ASCII_LOG_SEPARATORS", "Off")

    assert pm_module.normalize_log_separators("─────\n") == "─────\n"


# Verifies the logger writes to both the terminal and the log file, applying the separator conversion only to the file
def test_logger_writes_to_the_terminal_and_the_file(pm_module, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "ASCII_LOG_SEPARATORS", "On")
    log_file = tmp_path / "psn_monitor_user.log"

    logger = pm_module.Logger(str(log_file))
    try:
        logger.write("─────\n")
        logger.write("PSN user is now online\n")
    finally:
        logger.logfile.close()

    assert capsys.readouterr().out == "─────\nPSN user is now online\n"
    assert log_file.read_text(encoding="utf-8") == "-----\nPSN user is now online\n"


# Verifies tabs are expanded in the log file so the aligned output survives outside a terminal
def test_logger_expands_tabs_in_the_log_file(pm_module, tmp_path):
    log_file = tmp_path / "psn_monitor_user.log"

    logger = pm_module.Logger(str(log_file))
    try:
        logger.write("Status:\tONLINE\n")
    finally:
        logger.logfile.close()

    assert log_file.read_text(encoding="utf-8") == "Status: ONLINE\n"
