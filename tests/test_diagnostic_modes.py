"""Tests for --verbose and --debug: what the two modes report, and which setting wins.

Each coverage test drives the real code path with the failure injected rather than
calling the printers directly, so an uninstrumented path fails the test.
"""

import re
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
    def refuse(url, timeout=None, verify=None):
        raise requests.exceptions.ConnectionError("name resolution failed")

    monkeypatch.setattr(pm_module.req, "get", refuse)

    assert REAL_CHECK_INTERNET("https://psn.example/probe", 7) is False

    output = capsys.readouterr().out
    assert "Connectivity check: url=https://psn.example/probe, timeout=7s" in output
    assert "Connectivity check: url=https://psn.example/probe, outcome=failed, error=ConnectionError" in output


# Verifies a PSN call that fails inside the monitoring loop is named along with how it was classified
def test_debug_reports_the_presence_call_and_its_failure(pm_module, psn_session, fake_clock, both_modes_on, capsys):
    psn_session([presence_payload(status="offline"), requests.exceptions.ConnectionError("connection reset by peer")])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert f"PSNAWP session init: user={USER_ID}" in output
    assert f"Starting check: check=#1, user={USER_ID}, operation=PSN API get_presence()" in output
    assert "recovery_code=network.unavailable, policy=transient, outcome=failed, error=ConnectionError: connection reset by peer" in output


# Verifies an exception the tool swallows on purpose still leaves a trace under debug
def test_debug_reports_a_swallowed_exception(pm_module, both_modes_on, capsys):
    assert pm_module.get_date_from_ts("not-a-real-timestamp") == ""

    assert "Cannot parse timestamp: value=not-a-real-timestamp, format=full date" in capsys.readouterr().out


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

    assert f"Saved status written: path=psn_{USER_ID}_last_status.json" in first_run
    assert f"Saved status read: path=psn_{USER_ID}_last_status.json" in second_run


# Verifies a file the tool cannot write is reported with the reason, not only as a generic error
def test_debug_reports_a_failed_file_write(pm_module, psn_session, fake_clock, both_modes_on, isolated_working_directory, capsys):
    unwritable = isolated_working_directory / "history-dir"
    unwritable.mkdir()
    psn_session([presence_payload(status="offline", last_online="2026-01-01T00:00:00Z")])

    run_monitor(pm_module, str(unwritable))

    assert f"CSV initialization: path={unwritable}, outcome=failed, error=IsADirectoryError" in capsys.readouterr().out


# Verifies every wait names how long it is and why, so a stalled run can be explained from the transcript
def test_debug_reports_each_sleep_with_its_interval_and_reason(pm_module, psn_session, fake_clock, both_modes_on, capsys):
    psn_session([presence_payload(status="offline"), requests.exceptions.ConnectionError("connection reset by peer"), presence_payload(status="offline")])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert "Waiting: interval=3 minutes, reason=before the first check, status=offline" in output
    assert "Waiting: interval=15 seconds, reason=transient failure, streak=1" in output
    assert f"Completed check: check=#2, user={USER_ID}, outcome=OK" in output
    assert "next=3 minutes" in output
    # The failing check reports its own result, so the two ends of a check are told apart in one grep
    assert "Check: check=#1, recovery_code=network.unavailable, policy=transient, outcome=failed" in output


# Verifies recovering from a run of failures is reported, since nothing else marks the end of a streak
def test_recovery_after_a_reported_failure_streak_is_reported(pm_module, psn_session, fake_clock, capsys):
    psn_session([presence_payload(status="offline"), requests.exceptions.ConnectionError("first"), requests.exceptions.ConnectionError("second"), requests.exceptions.ConnectionError("third"), presence_payload(status="offline")])

    run_monitor(pm_module)

    assert f"* Monitoring recovered for {USER_ID} after " in capsys.readouterr().out


# Verifies a blip too short to be reported produces no recovery line either, so verbose stays quiet on both sides
def test_verbose_stays_quiet_when_the_streak_was_never_reported(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    psn_session([presence_payload(status="offline"), requests.exceptions.ConnectionError("first"), presence_payload(status="offline")])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert "Monitoring recovered for" not in output
    assert "connection reset" not in output


# Verifies a single reported failure reports its recovery too, so one bad check does not read as a lasting outage
def test_a_single_reported_failure_reports_its_recovery(pm_module, psn_session, fake_clock, capsys):
    psn_session([presence_payload(status="offline"), presence_payload(status=None), presence_payload(status="offline")])

    run_monitor(pm_module)

    assert f"* Monitoring recovered for {USER_ID} after " in capsys.readouterr().out


# Verifies the config file and the source of every secret are reported, which is what a wrong-credential report needs
def test_debug_reports_the_config_load_and_the_secret_source(pm_module, monkeypatch, monitor_calls, isolated_working_directory, capsys):
    config = isolated_working_directory / "custom.conf"
    config.write_text('PSN_NPSSO = "npsso-from-config"\nPSN_CHECK_INTERVAL = 300\n', encoding="utf-8")

    run_main(pm_module, monkeypatch, ["--config-file", str(config), "--debug", USER_ID])

    output = capsys.readouterr().out
    assert f"Configuration applied: path={config}, settings=2, names=PSN_CHECK_INTERVAL, PSN_NPSSO" in output
    assert "Secret resolution: name=PSN_NPSSO, source=configuration file, value=set, chars=17" in output
    # A password the user chose is reported as present only, since debug output is what bug reports carry
    assert "Secret resolution: name=SMTP_PASSWORD, source=" in output and "value=set" in output
    assert f"chars={len(pm_module.SMTP_PASSWORD)}" not in output


# Verifies a secret supplied on the command line is reported as such, without any part of its value
def test_debug_never_prints_the_credential_it_reports(pm_module, monkeypatch, monitor_calls, capsys):
    run_main(pm_module, monkeypatch, ["--debug", "-n", "aVeryLongNpssoValue1234567890", USER_ID])

    output = capsys.readouterr().out
    assert "Secret resolution: name=PSN_NPSSO, source=command line, value=set, chars=29" in output
    # The length belongs to its own field, so a reader can split the line on ", " and get pairs
    trace = [line for line in output.splitlines() if "Secret resolution: name=PSN_NPSSO, source=command line" in line][0].split("Secret resolution: ", 1)[1]
    assert dict(field.split("=", 1) for field in trace.split(", ")) == {"name": "PSN_NPSSO", "source": "command line", "value": "set", "chars": "29"}
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

    assert f"Configuration rejected: path={config}, reason=Config file" in capsys.readouterr().out


# Verifies turning one mode on does not turn the other on
def test_the_two_modes_are_independent(pm_module, monkeypatch, monitor_calls, capsys):
    run_main(pm_module, monkeypatch, ["--verbose", "-n", "npsso-test-value", USER_ID])
    verbose_only = capsys.readouterr().out

    # A real process runs main() once, so the second run starts from the shipped defaults again
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", False)
    run_main(pm_module, monkeypatch, ["--debug", "-n", "npsso-test-value", USER_ID])
    debug_only = capsys.readouterr().out

    assert "[DEBUG " not in verbose_only
    assert "[DEBUG " in debug_only
    # The startup summary reports each mode separately, so one flag must never switch the other on
    assert re.search(r"\* Verbose mode:\s+True", verbose_only) and re.search(r"\* Debug mode:\s+False", verbose_only)
    assert re.search(r"\* Verbose mode:\s+False", debug_only) and re.search(r"\* Debug mode:\s+True", debug_only)


# Verifies neither mode prints anything on a run that exercises the paths both of them instrument
def test_neither_mode_prints_anything_when_both_are_off(pm_module, psn_session, fake_clock, capsys):
    psn_session([presence_payload(status="offline"), requests.exceptions.ConnectionError("connection reset by peer"), presence_payload(status="offline")])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert "[DEBUG " not in output
    assert "Monitoring recovered for" not in output
    assert "Waiting:" not in output


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


# Verifies the settings count is a debug trace rather than a verbose line, since it says nothing a user acts on
def test_the_config_settings_count_is_a_debug_only_trace(pm_module, tmp_path, monkeypatch, capsys):
    config = tmp_path / "psn_monitor.conf"
    config.write_text("CLEAR_SCREEN = False\nDISABLE_LOGGING = True\n", encoding="utf-8")
    namespace = {}

    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(pm_module, "DEBUG_MODE", False)
    pm_module.load_config_file(config, namespace=namespace)
    assert "settings from the configuration file" not in capsys.readouterr().out

    monkeypatch.setattr(pm_module, "VERBOSE_MODE", False)
    monkeypatch.setattr(pm_module, "DEBUG_MODE", True)
    pm_module.load_config_file(config, namespace=namespace)
    assert "Configuration applied" in capsys.readouterr().out


# Verifies only debug keeps the screen, since a cleared terminal loses the run being compared against
@pytest.mark.parametrize(("flag", "expected"), (("--debug", False), ("--verbose", True)))
def test_only_debug_mode_keeps_the_screen(pm_module, monkeypatch, monitor_calls, flag, expected):
    cleared = []
    monkeypatch.setattr(pm_module, "clear_screen", lambda enabled=True: cleared.append(bool(enabled)))
    monkeypatch.setattr(pm_module, "CLEAR_SCREEN", True)
    monkeypatch.setattr(pm_module, "DEBUG_MODE", False)
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", False)

    run_main(pm_module, monkeypatch, ["test-user", "--env-file", "none", flag])

    assert cleared == [expected]


# Verifies the one-shot commands keep whatever is already on the screen, so their output stays scrollable
@pytest.mark.parametrize(("argv", "expected"), ((["psn_monitor", "--doctor"], True), (["psn_monitor", "--set-npsso"], True), (["psn_monitor", "--send-test-email"], True), (["psn_monitor", "--help"], True), (["psn_monitor", "test-user"], False)))
def test_one_shot_commands_keep_the_terminal_history(pm_module, monkeypatch, argv, expected):
    monkeypatch.setattr(pm_module.sys, "argv", argv)

    assert pm_module.keep_terminal_history() is expected


# Verifies a redirected stdout is never cleared, so no escape sequence or TERM warning reaches the captured output
def test_a_redirected_stdout_is_never_cleared(pm_module, monkeypatch):
    commands = []
    monkeypatch.setattr(pm_module.sys.stdout, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(pm_module.os, "system", lambda command: commands.append(command))

    pm_module.clear_screen(True)

    assert commands == []


# A secret no layer supplied takes no row, so the trace lists what is configured rather than what is not
def test_the_trace_omits_every_secret_no_layer_supplied(pm_module, monkeypatch, monitor_calls, capsys):
    run_main(pm_module, monkeypatch, ["--debug", "-n", "aVeryLongNpssoValue1234567890", USER_ID])

    output = capsys.readouterr().out
    assert "Secret resolution: name=PSN_NPSSO, source=command line" in output
    assert "name=NTFY_ACCESS_TOKEN" not in output
    assert "source=nowhere" not in output
    assert "No private settings were resolved" not in output


# A run where no layer supplied anything says so once, rather than printing a row per unset key
def test_a_run_with_no_secrets_says_so_once(pm_module, monkeypatch, monitor_calls, capsys):
    monkeypatch.setattr(pm_module, "SECRET_SOURCES", {})
    for name in pm_module.SECRET_KEYS:
        monkeypatch.setattr(pm_module, name, "", raising=False)
        monkeypatch.delenv(name, raising=False)

    run_main(pm_module, monkeypatch, ["--debug", "--config-file", "none", "--env-file", "none", USER_ID])

    output = capsys.readouterr().out
    assert output.count("No private settings were resolved from config, dotenv, environment or the command line") == 1
    assert "Secret resolution: " not in output


# The trace runs after the last layer, so one secret cannot be reported twice with opposite answers
def test_the_trace_reports_a_command_line_secret_exactly_once(pm_module, monkeypatch, monitor_calls, capsys):
    run_main(pm_module, monkeypatch, ["--debug", "-n", "aVeryLongNpssoValue1234567890", USER_ID])

    traces = [line for line in capsys.readouterr().out.splitlines() if "Secret resolution: name=PSN_NPSSO" in line]
    assert len(traces) == 1


# A placeholder is not a value, so it earns neither a source nor a row, which is what the doctor already reports
def test_a_placeholder_earns_no_source(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "SECRET_SOURCES", {})
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "your_psn_npsso_code", raising=False)

    pm_module.record_secret_source("PSN_NPSSO", "dotenv file")

    assert pm_module.SECRET_SOURCES == {}
    with pytest.raises(ValueError, match="Unsupported secret source"):
        pm_module.record_secret_source("PSN_NPSSO", "a layer that does not exist", "a real value")
