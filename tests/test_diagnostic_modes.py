"""Tests for --verbose and --debug: what the two modes report, and which setting wins.

Each coverage test drives the real code path with the failure injected rather than
calling the printers directly, so an uninstrumented path fails the test.
"""

import sys

import pytest
import requests

import psn_monitor

from conftest import LoopFinished, presence_payload


USER_ID = "misiektoja"

# Captured before the fixture below replaces it, so the connectivity test can drive the real function
REAL_CHECK_INTERNET = psn_monitor.check_internet


@pytest.fixture(autouse=True)
# Keeps the state file, the CSV history and any generated config inside the test directory
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
    monkeypatch.setattr(pm_module, "probe_npsso_auth_error", lambda npsso: None)


@pytest.fixture
# Turns both diagnostic modes on for tests that only care about what gets reported
def both_modes_on(monkeypatch, pm_module):
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(pm_module, "DEBUG_MODE", True)


@pytest.fixture
# Replaces the monitoring loop with a recorder so main() returns after startup
def monitor_calls(monkeypatch, pm_module):
    recorded = []

    # Records the arguments the monitoring loop was started with
    def fake_monitor(psn_user_id, csv_file_name):
        recorded.append(psn_user_id)

    monkeypatch.setattr(pm_module, "psn_monitor_user", fake_monitor)
    return recorded


# Runs main() with the supplied command line and returns the exit code it raised
def run_main(pm_module, monkeypatch, argv):
    monkeypatch.setattr(pm_module.sys, "argv", ["psn_monitor", *argv])
    with pytest.raises(SystemExit) as raised:
        pm_module.main()
    return raised.value.code


# Runs the monitoring loop until the scripted responses are exhausted
def run_monitor(pm_module, csv_file_name=""):
    with pytest.raises(LoopFinished):
        pm_module.psn_monitor_user(USER_ID, csv_file_name)


# Verifies a failed connectivity check names the address and the timeout it used
def test_debug_reports_the_connectivity_check(pm_module, monkeypatch, both_modes_on, capsys):
    monkeypatch.setattr(pm_module, "CHECK_INTERNET_URL", "https://psn.example/probe", raising=False)
    monkeypatch.setattr(pm_module, "CHECK_INTERNET_TIMEOUT", 7, raising=False)

    # Fails the way a broken network does, so the real error branch runs
    def refuse(url, timeout=None):
        raise requests.exceptions.ConnectionError("name resolution failed")

    monkeypatch.setattr(pm_module.req, "get", refuse)

    assert REAL_CHECK_INTERNET("https://psn.example/probe", 7) is False

    output = capsys.readouterr().out
    assert "HTTP GET https://psn.example/probe (connectivity check, timeout 7s)" in output
    assert "HTTP GET https://psn.example/probe failed: ConnectionError" in output


# Verifies a PSN call that fails inside the monitoring loop is named along with how it was classified
def test_debug_reports_the_presence_call_and_its_failure(pm_module, psn_session, fake_clock, both_modes_on, capsys):
    psn_session([presence_payload(status="offline"), requests.exceptions.ConnectionError("connection reset by peer")])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert f"PSNAWP session init for PSN user '{USER_ID}'" in output
    assert f"Starting check #1 for '{USER_ID}', PSN API get_presence()" in output
    assert "classified as 'network.unavailable' under the transient retry policy: ConnectionError: connection reset by peer" in output


# Verifies an exception the tool swallows on purpose still leaves a trace under debug
def test_debug_reports_a_swallowed_exception(pm_module, both_modes_on, capsys):
    assert pm_module.get_date_from_ts("not-a-real-timestamp") == ""

    assert "Cannot parse timestamp 'not-a-real-timestamp' for the full date format" in capsys.readouterr().out


# Verifies a feature that quietly turns itself off says so, instead of looking like it is working
def test_a_degraded_feature_is_reported_without_debug_mode(pm_module, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "wcwidth", None)

    assert pm_module.resolve_truncate_chars(120, 0, False) == 0
    output = capsys.readouterr().out
    assert "Screen truncation is disabled because the optional 'wcwidth' library is missing" in output
    # Reported as a warning, since the tool keeps running without it
    assert output.startswith("* Warning:")
    assert "-m pip install wcwidth" in output


# Verifies both outcomes of writing the status file are visible, not only the failure
def test_debug_reports_the_status_file_on_both_branches(pm_module, psn_session, fake_clock, both_modes_on, isolated_working_directory, capsys):
    psn_session([presence_payload(status="offline", last_online="2026-01-01T00:00:00Z")])

    run_monitor(pm_module)
    first_run = capsys.readouterr().out

    psn_session([presence_payload(status="offline", last_online="2026-01-01T00:00:00Z")])
    run_monitor(pm_module)
    second_run = capsys.readouterr().out

    assert f"Saved status written to 'psn_{USER_ID}_last_status.json'" in first_run
    assert f"Saved status read from 'psn_{USER_ID}_last_status.json'" in second_run


# Verifies a file the tool cannot write is reported with the reason, not only as a generic error
def test_debug_reports_a_failed_file_write(pm_module, psn_session, fake_clock, both_modes_on, isolated_working_directory, capsys):
    unwritable = isolated_working_directory / "history-dir"
    unwritable.mkdir()
    psn_session([presence_payload(status="offline", last_online="2026-01-01T00:00:00Z")])

    run_monitor(pm_module, str(unwritable))

    assert f"CSV file '{unwritable}' could not be initialized: IsADirectoryError" in capsys.readouterr().out


# Verifies every wait names how long it is and why, so a stalled run can be explained from the transcript
def test_debug_reports_each_sleep_with_its_interval_and_reason(pm_module, psn_session, fake_clock, both_modes_on, capsys):
    psn_session([presence_payload(status="offline"), requests.exceptions.ConnectionError("connection reset by peer"), presence_payload(status="offline")])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert "Sleeping 3 minutes before the first check (status: offline)" in output
    assert "Sleeping 15 seconds after a transient failure (streak: 1)" in output
    assert f"Check #2 done for '{USER_ID}'" in output
    assert "next check in 3 minutes" in output


# Verifies recovering from a run of failures is reported, since nothing else marks the end of a streak
def test_verbose_reports_recovery_after_a_failure_streak(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    psn_session([presence_payload(status="offline"), requests.exceptions.ConnectionError("first"), requests.exceptions.ConnectionError("second"), presence_payload(status="offline")])

    run_monitor(pm_module)

    assert "* Recovered after 2 failed checks in a row" in capsys.readouterr().out


# Verifies the config file and the source of every secret are reported, which is what a wrong-credential report needs
def test_debug_reports_the_config_load_and_the_secret_source(pm_module, monkeypatch, monitor_calls, isolated_working_directory, capsys):
    config = isolated_working_directory / "custom.conf"
    config.write_text('PSN_NPSSO = "npsso-from-config"\nPSN_CHECK_INTERVAL = 300\n', encoding="utf-8")

    run_main(pm_module, monkeypatch, ["--config-file", str(config), "--debug", USER_ID])

    output = capsys.readouterr().out
    assert f"Config file '{config}' applied 2 settings: PSN_CHECK_INTERVAL, PSN_NPSSO" in output
    assert "Secret PSN_NPSSO is set, 17 chars, resolved from configuration file" in output


# Verifies a secret supplied on the command line is reported as such, without any part of its value
def test_debug_never_prints_the_credential_it_reports(pm_module, monkeypatch, monitor_calls, capsys):
    run_main(pm_module, monkeypatch, ["--debug", "-n", "aVeryLongNpssoValue1234567890", USER_ID])

    output = capsys.readouterr().out
    assert "PSN_NPSSO taken from the command line (set, 29 chars)" in output
    assert "aVeryLongNpssoValue1234567890" not in output


# Verifies a flag that was typed wins over the config file setting, in both directions
@pytest.mark.parametrize("setting, flag, expected", [
    ("DEBUG_MODE = False", "--debug", True),
    ("DEBUG_MODE = True", None, True),
    ("DEBUG_MODE = False", None, False),
])
def test_the_typed_debug_flag_wins_over_the_config_file(pm_module, monkeypatch, monitor_calls, isolated_working_directory, capsys, setting, flag, expected):
    config = isolated_working_directory / "custom.conf"
    config.write_text(f"{setting}\n", encoding="utf-8")

    run_main(pm_module, monkeypatch, ["--config-file", str(config), *([flag] if flag else []), "-n", "npsso-test-value", USER_ID])

    assert ("[DEBUG " in capsys.readouterr().out) is expected


# Verifies debug output starts before the config file is read, so a broken config is still diagnosable
def test_the_debug_flag_applies_before_the_config_file_is_read(pm_module, monkeypatch, isolated_working_directory, capsys):
    config = isolated_working_directory / "broken.conf"
    config.write_text("PSN_CHECK_INTERVAL = = 300\n", encoding="utf-8")

    assert run_main(pm_module, monkeypatch, ["--config-file", str(config), "--debug", USER_ID]) == 1

    assert f"Config file '{config}' rejected: Config file" in capsys.readouterr().out


# Verifies turning one mode on does not turn the other on
def test_the_two_modes_are_independent(pm_module, monkeypatch, monitor_calls, capsys):
    run_main(pm_module, monkeypatch, ["--verbose", "-n", "npsso-test-value", USER_ID])
    verbose_only = capsys.readouterr().out

    # A real process runs main() once, so the second run starts from the shipped defaults again
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", False)
    run_main(pm_module, monkeypatch, ["--debug", "-n", "npsso-test-value", USER_ID])
    debug_only = capsys.readouterr().out

    assert "[DEBUG " not in verbose_only
    assert "* Local timezone resolved to" in verbose_only
    assert "[DEBUG " in debug_only
    assert "* Local timezone resolved to" not in debug_only


# Verifies neither mode prints anything on a run that exercises the paths both of them instrument
def test_neither_mode_prints_anything_when_both_are_off(pm_module, psn_session, fake_clock, capsys):
    psn_session([presence_payload(status="offline"), requests.exceptions.ConnectionError("connection reset by peer"), presence_payload(status="offline")])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert "[DEBUG " not in output
    assert "Recovered after" not in output
    assert "Sleeping " not in output


# Verifies the startup summary points at the flags while they are off, and reports them once they are on
def test_the_startup_summary_offers_the_flags_then_reports_them(pm_module, monkeypatch, monitor_calls, capsys):
    run_main(pm_module, monkeypatch, ["-n", "npsso-test-value", USER_ID])
    without_flags = capsys.readouterr().out

    run_main(pm_module, monkeypatch, ["--verbose", "-n", "npsso-test-value", USER_ID])
    with_verbose = capsys.readouterr().out

    assert "use --verbose or --debug" in without_flags
    assert "* More details:" not in with_verbose
    assert "Verbose mode:" in with_verbose
    assert "Debug mode:" in with_verbose
    # The concise view stays short, and asking for the full one is what adds the rest
    assert without_flags.count("\n* ") < with_verbose.count("\n* ")
