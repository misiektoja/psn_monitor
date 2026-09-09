"""Offline end-to-end tests that drive the monitoring loop with scripted PSN responses."""

import json

import pytest
import requests

from conftest import LoopFinished, presence_payload

psnawp_exceptions = pytest.importorskip("psnawp_api.core.psnawp_exceptions")

USER_ID = "misiektoja"
LAST_STATUS_FILE = f"psn_{USER_ID}_last_status.json"


@pytest.fixture(autouse=True)
# Keeps the state file, the CSV history and the log inside the test directory
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
# Keeps the auth probe offline, since the error paths call it before deciding what to report
def offline_auth_probe(monkeypatch, pm_module):
    monkeypatch.setattr(pm_module, "probe_npsso_auth_error", lambda npsso: None)


# Runs the monitoring loop until the scripted responses are exhausted
def run_monitor(pm_module, csv_file_name=""):
    with pytest.raises(LoopFinished):
        pm_module.psn_monitor_user(USER_ID, csv_file_name)


# Verifies the tool reports the profile it is monitoring before the first poll
def test_startup_reports_the_monitored_profile(pm_module, psn_session, fake_clock, capsys):
    psn_session([presence_payload(status="offline", platform_code="PS5", last_online="2026-01-01T00:00:00Z")])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert f"PlayStation ID:\t\t\t{USER_ID}" in output
    assert "PSN account ID:\t\t\t1234567890" in output
    assert "Status:\t\t\t\tOFFLINE" in output
    assert "Platform:\t\t\tPlayStation 5" in output
    assert "PS+ user:\t\t\tTrue" in output
    assert "Relation:\t\t\tfriend" in output
    assert "Mutual friends:\t\t\t3" in output
    assert "https://psn.example/misiektoja" in output


# Verifies a user who is already in a game at startup is reported as in-game with the launch platform
def test_startup_reports_an_in_progress_session(pm_module, psn_session, fake_clock, capsys):
    psn_session([presence_payload(status="online", game="Marvel’s Spider-Man", launch_platform="ps5")])

    run_monitor(pm_module)

    assert "User is currently in-game:\tMarvel's Spider-Man (PS5)" in capsys.readouterr().out


# Verifies the first run records the status so a restart does not lose the current session
def test_first_run_records_the_status_file(pm_module, psn_session, fake_clock, isolated_working_directory):
    psn_session([presence_payload(status="offline", last_online="2026-01-01T00:00:00Z")])

    run_monitor(pm_module)

    recorded = json.loads((isolated_working_directory / LAST_STATUS_FILE).read_text(encoding="utf-8"))
    assert recorded == [1767225600, "offline"]


# Verifies a restart picks up the recorded status instead of treating the user as newly seen
def test_restart_reads_the_recorded_status(pm_module, psn_session, fake_clock, isolated_working_directory, capsys):
    (isolated_working_directory / LAST_STATUS_FILE).write_text(json.dumps([1767225600, "offline"]), encoding="utf-8")
    psn_session([presence_payload(status="offline")])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert f"Last status loaded from file '{LAST_STATUS_FILE}'" in output
    assert "Last status read from file: OFFLINE" in output
    assert "Last time user was available:" in output


# Verifies going online is announced, recorded and emailed once the operator asked for status alerts
def test_user_going_online_is_announced_and_emailed(pm_module, psn_session, fake_clock, monkeypatch, sent_emails, isolated_working_directory, capsys):
    monkeypatch.setattr(pm_module, "ACTIVE_INACTIVE_NOTIFICATION", True)
    psn_session([presence_payload(status="offline"), presence_payload(status="online")])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert f"PSN user {USER_ID} changed status from offline to online" in output
    assert "*** User got ACTIVE !" in output
    assert len(sent_emails) == 1
    assert sent_emails[0]["subject"].startswith(f"PSN user {USER_ID} is now online")
    assert json.loads((isolated_working_directory / LAST_STATUS_FILE).read_text(encoding="utf-8"))[1] == "online"


# Verifies going offline reports how long the session lasted and how many games were played
def test_user_going_offline_summarizes_the_session(pm_module, psn_session, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(pm_module, "ACTIVE_INACTIVE_NOTIFICATION", True)
    psn_session([
        presence_payload(status="online", game="Bloodborne"),
        presence_payload(status="online", game="Bloodborne"),
        presence_payload(status="offline"),
    ])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert "*** User got OFFLINE !" in output
    assert "User played 1 games for total time of" in output
    assert any("is now offline" in message["subject"] for message in sent_emails)


# Verifies a brief disconnect is folded back into the running session instead of starting a new one
def test_short_offline_interruption_restores_the_session_start(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "OFFLINE_INTERRUPT", 420)
    psn_session([
        presence_payload(status="online"),
        presence_payload(status="offline"),
        presence_payload(status="online"),
    ])

    run_monitor(pm_module)

    assert "Short offline interruption" in capsys.readouterr().out


# Verifies a disconnect longer than the configured window starts a fresh session
def test_long_offline_gap_starts_a_new_session(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "OFFLINE_INTERRUPT", 60)
    psn_session([
        presence_payload(status="online"),
        presence_payload(status="offline"),
        presence_payload(status="online"),
    ])

    run_monitor(pm_module)

    assert "Short offline interruption" not in capsys.readouterr().out


# Verifies starting, changing and stopping a game each produce their own alert
def test_game_start_change_and_stop_are_each_reported(pm_module, psn_session, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(pm_module, "GAME_CHANGE_NOTIFICATION", True)
    psn_session([
        presence_payload(status="online"),
        presence_payload(status="online", game="Bloodborne", launch_platform="ps4"),
        presence_payload(status="online", game="Elden Ring", launch_platform="ps5"),
        presence_payload(status="online"),
    ])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert f"PSN user {USER_ID} started playing 'Bloodborne' (PS4)" in output
    assert f"PSN user {USER_ID} changed game from 'Bloodborne' to 'Elden Ring' (PS5)" in output
    assert f"PSN user {USER_ID} stopped playing 'Elden Ring'" in output
    subjects = [message["subject"] for message in sent_emails]
    assert len(subjects) == 3
    assert "now plays 'Bloodborne'" in subjects[0]
    assert "changed game to 'Elden Ring'" in subjects[1]
    assert "stopped playing 'Elden Ring'" in subjects[2]


# Verifies game titles are normalized before they reach the log and the notification
def test_game_titles_are_normalized_before_they_are_reported(pm_module, psn_session, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(pm_module, "GAME_CHANGE_NOTIFICATION", True)
    psn_session([presence_payload(status="online"), presence_payload(status="online", game="Ratchet & Clank™: Rift Apart®")])

    run_monitor(pm_module)

    assert "Ratchet & Clank: Rift Apart" in capsys.readouterr().out
    assert "Ratchet & Clank: Rift Apart" in sent_emails[0]["subject"]


# Verifies nothing is emailed while the notification flags are off, however much the user does
def test_no_email_is_sent_while_notifications_are_off(pm_module, psn_session, fake_clock, sent_emails):
    psn_session([
        presence_payload(status="offline"),
        presence_payload(status="online", game="Bloodborne"),
        presence_payload(status="offline"),
    ])

    run_monitor(pm_module)

    assert sent_emails == []


# Verifies every status and game change lands in the CSV history in order
def test_changes_are_appended_to_the_csv_history(pm_module, psn_session, fake_clock, isolated_working_directory):
    import csv

    history = isolated_working_directory / "history.csv"
    psn_session([
        presence_payload(status="offline"),
        presence_payload(status="online"),
        presence_payload(status="online", game="Bloodborne"),
        presence_payload(status="offline"),
    ])

    run_monitor(pm_module, csv_file_name=str(history))

    rows = list(csv.DictReader(history.open(encoding="utf-8")))
    assert [row["Status"] for row in rows] == ["offline", "online", "online", "offline"]
    assert [row["Game name"] for row in rows] == ["", "", "Bloodborne", ""]


# Verifies an expired NPSSO is reported with a recovery hint and alerted on exactly once
def test_expired_npsso_is_reported_and_alerted_once(pm_module, psn_session, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)
    psn_session([
        presence_payload(status="offline"),
        psnawp_exceptions.PSNAWPAuthenticationError("Your npsso code has expired"),
        psnawp_exceptions.PSNAWPAuthenticationError("Your npsso code has expired"),
    ])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert "rejected the NPSSO code" in output
    assert "send SIGHUP to this process" in output
    assert len(sent_emails) == 1
    assert "rejected the NPSSO code" in sent_emails[0]["subject"]


# Verifies the Terms of Service hint replaces the raw library error when the probe recognizes it
def test_terms_of_service_hint_replaces_the_raw_error(pm_module, psn_session, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "probe_npsso_auth_error", lambda npsso: "PSN Terms of Service / User Agreement must be re-accepted.")
    psn_session([presence_payload(status="offline"), Exception("Something went wrong while authenticating")])

    run_monitor(pm_module)

    assert "Terms of Service" in capsys.readouterr().out
    assert "Terms of Service" in sent_emails[0]["body"]


# Verifies an alert that lands on a check the outage reporter keeps quiet still ends with a timestamp
def test_a_delivery_on_a_quiet_check_ends_with_a_timestamp(pm_module, psn_session, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)
    broken = presence_payload(status="offline")
    broken["basicPresence"]["primaryPlatformInfo"] = None
    psn_session([presence_payload(status="offline"), broken, broken, broken, broken])

    run_monitor(pm_module)

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    deliveries = [index for index, line in enumerate(lines) if line.startswith("Sending email notification")]

    assert deliveries, lines
    for index in deliveries:
        assert any(line.startswith("Timestamp:") for line in lines[index + 1:index + 3]), lines[index:index + 3]


# Verifies a session rebuild announced on a check the outage reporter keeps quiet still ends with a timestamp
def test_a_session_rebuild_on_a_quiet_check_ends_with_a_timestamp(pm_module, psn_session, fake_clock, capsys):
    psn_session([presence_payload(status="offline")] + [RuntimeError("unrecognized failure") for _ in range(6)])

    run_monitor(pm_module)

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    rebuilds = [index for index, line in enumerate(lines) if line.startswith("* Rebuilt the PSNAWP session")]

    assert rebuilds, lines
    for index in rebuilds:
        assert any(line.startswith("Timestamp:") for line in lines[index + 1:index + 3]), lines[index:index + 3]


# Verifies a malformed presence response rebuilds the session rather than being treated as an outage
def test_malformed_response_recreates_the_session(pm_module, psn_session, fake_clock, capsys):
    broken = presence_payload(status="offline")
    broken["basicPresence"]["primaryPlatformInfo"] = None
    psn_session([presence_payload(status="offline"), broken, presence_payload(status="offline")])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert "unexpected shape" in output
    assert "Rebuilt the PSNAWP session after 1 failed check in a row" in output


# Verifies repeated malformed responses raise an alert only once the problem is clearly persistent
def test_persistent_malformed_responses_alert_once(pm_module, psn_session, fake_clock, monkeypatch, sent_emails):
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)
    broken = presence_payload(status="offline")
    broken["basicPresence"]["primaryPlatformInfo"] = None
    psn_session([presence_payload(status="offline"), broken, broken, broken, broken])

    run_monitor(pm_module)

    assert len(sent_emails) == 1
    assert "unexpected shape" in sent_emails[0]["subject"]


# Verifies an empty status is treated as a malformed response instead of an offline user
def test_empty_status_is_treated_as_malformed(pm_module, psn_session, fake_clock, capsys):
    psn_session([presence_payload(status="offline"), presence_payload(status=None)])

    run_monitor(pm_module)

    assert "unexpected shape" in capsys.readouterr().out


# Verifies short network outages are retried quietly without alerting the operator
def test_short_network_outages_are_retried_quietly(pm_module, psn_session, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)
    psn_session([
        presence_payload(status="offline"),
        requests.exceptions.ConnectionError("connection reset by peer"),
        requests.exceptions.ConnectionError("connection reset by peer"),
        presence_payload(status="online"),
    ])

    run_monitor(pm_module)

    assert sent_emails == []
    assert "changed status from offline to online" in capsys.readouterr().out


# Verifies a longer outage rebuilds the session and starts reporting the retries
def test_longer_network_outage_recreates_the_session(pm_module, psn_session, fake_clock, capsys):
    outage = [requests.exceptions.ConnectionError("connection reset by peer")] * 4
    psn_session([presence_payload(status="offline"), *outage])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert "Rebuilt the PSNAWP session after 3 failed checks in a row" in output
    assert "could not be reached (retrying in" in output


# Verifies a lasting outage reports itself once and then only on the liveness cadence
def test_a_lasting_outage_rides_the_liveness_cadence(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "LIVENESS_REMINDER_SECONDS", 2 * pm_module.FUNCTION_TIMEOUT)
    outage = [requests.exceptions.ConnectionError("connection reset by peer")] * 8
    psn_session([presence_payload(status="offline"), *outage])

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert output.count("To fix: ") == 1
    assert f"* Monitoring degraded for {USER_ID}. " in output
    assert "could not be reached since " in output


# Verifies the reminder follows the clock, so a run that retries faster than it polls does not remind more often
def test_the_outage_reminder_follows_the_clock_not_the_check_count(pm_module, fake_clock):
    reporter = pm_module.OutageReporter()
    advice = pm_module.classify_recovery_error(requests.exceptions.ConnectionError("connection reset by peer"), context="monitor")

    assert reporter.failed(advice, 900) == "full"
    outcomes = []
    for _ in range(60):
        fake_clock.advance(15)
        outcomes.append(reporter.failed(advice, 900))

    assert outcomes.count("degraded") == 1


# Verifies a long outage announces the session rebuild once rather than on every cooldown
def test_the_session_rebuild_is_announced_once_per_outage(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "LIVENESS_REMINDER_SECONDS", 43200)
    psn_session([presence_payload(status="offline"), *[requests.exceptions.ConnectionError("connection reset by peer")] * 60])

    run_monitor(pm_module)

    assert capsys.readouterr().out.count("* Rebuilt the PSNAWP session") == 1


# Verifies rebuilding the session closes the HTTP session of the replaced client instead of leaking its connection pool
def test_session_recreation_closes_the_previous_session(pm_module, psn_session, fake_clock):
    broken = presence_payload(status="offline")
    broken["basicPresence"]["primaryPlatformInfo"] = None
    psn_session([presence_payload(status="offline"), broken, presence_payload(status="offline")])

    run_monitor(pm_module)

    replaced, current = psn_session.instances
    assert replaced.authenticator.request_builder.session.closed is True
    assert current.authenticator.request_builder.session.closed is False


# Verifies local file descriptor exhaustion stops the tool with an actionable message rather than looping
def test_descriptor_exhaustion_stops_the_tool(pm_module, psn_session, fake_clock, monkeypatch, sent_emails, capsys):
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)
    psn_session([presence_payload(status="offline"), OSError(24, "Too many open files")])

    with pytest.raises(SystemExit) as raised:
        pm_module.psn_monitor_user(USER_ID, "")

    assert raised.value.code == 2
    output = capsys.readouterr().out
    assert "ran out of file descriptors" in output
    assert "ulimit -n 4096" in output
    assert "ran out of file descriptors" in sent_emails[0]["subject"]


# Verifies a rotated NPSSO is picked up on the next poll without a restart
def test_rotated_npsso_rebuilds_the_session(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    # Rotates the token the way a SIGHUP-driven reload does, between two polls
    def rotate_and_report():
        monkeypatch.setattr(pm_module, "PSN_NPSSO", "rotated-npsso-value")
        return presence_payload(status="offline")

    psn_session([presence_payload(status="offline"), rotate_and_report, presence_payload(status="offline")])

    run_monitor(pm_module)

    assert "PSN_NPSSO updated - recreated PSNAWP session" in capsys.readouterr().out
    assert [client.npsso for client in psn_session.instances] == ["npsso-test-value", "rotated-npsso-value"]
    assert psn_session.instances[0].authenticator.request_builder.session.closed is True


# Verifies verbose stays quiet on an uneventful cycle instead of printing one line per check
def test_a_quiet_cycle_stays_silent_in_verbose(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    psn_session([presence_payload(status="offline")] * 3)

    run_monitor(pm_module)

    assert "Monitoring check #" not in capsys.readouterr().out


# Verifies a verbose notice closes with the shared timestamp trailer instead of floating between blocks
def test_a_verbose_notice_closes_with_a_timestamp(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)

    # Rotates the token the way a SIGHUP-driven reload does, between two polls
    def rotate_and_report():
        monkeypatch.setattr(pm_module, "PSN_NPSSO", "rotated-npsso-value")
        return presence_payload(status="offline")

    psn_session([presence_payload(status="offline"), rotate_and_report, presence_payload(status="offline")])

    run_monitor(pm_module)

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    notice = next(index for index, line in enumerate(lines) if "recreating the PSNAWP session" in line)
    assert lines[notice + 1].startswith("Timestamp:")
    assert set(lines[notice + 2]) == {"\u2500"}


# Verifies a notice printed before monitoring starts stays a bare line, since the monitoring header closes that block
def test_a_verbose_notice_stays_bare_on_the_startup_screen(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(pm_module, "MONITORING_ACTIVE", False)

    pm_module.verbose_notice("Recreated the PSNAWP session")

    assert capsys.readouterr().out == "* Recreated the PSNAWP session\n"


# Verifies the liveness line is printed while an offline user produces no other output
def test_liveness_check_reports_the_loop_is_alive(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "LIVENESS_REMINDER_SECONDS", 2 * pm_module.PSN_CHECK_INTERVAL)
    psn_session([presence_payload(status="offline")] * 4)

    run_monitor(pm_module)

    assert "Liveness check, timestamp:" in capsys.readouterr().out


# Verifies the banner follows the clock, so a user polled on the shorter active interval is not reminded more often
def test_the_liveness_banner_follows_the_clock_not_the_check_count(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "LIVENESS_REMINDER_SECONDS", 4 * pm_module.PSN_ACTIVE_CHECK_INTERVAL)
    psn_session([presence_payload(status="online")] * 6)

    run_monitor(pm_module)

    assert capsys.readouterr().out.count("Monitoring healthy for") == 1


# Verifies an online user still reports the liveness line, since nothing changed there either
def test_liveness_check_reports_an_online_user(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "LIVENESS_REMINDER_SECONDS", 2 * pm_module.PSN_ACTIVE_CHECK_INTERVAL)
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    psn_session([presence_payload(status="online")] * 4)

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert "Monitoring healthy for" in output
    assert "The user is online with no activity change since the last check" in output
    assert "Liveness check, timestamp:" in output


# Verifies the banner explains itself without --verbose too, so a plain run never prints a bare timestamp
def test_the_liveness_banner_explains_itself_without_diagnostics(pm_module, psn_session, fake_clock, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "LIVENESS_REMINDER_SECONDS", 2 * pm_module.PSN_CHECK_INTERVAL)
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", False)
    psn_session([presence_payload()] * 4)

    run_monitor(pm_module)

    output = capsys.readouterr().out
    assert "* Monitoring healthy for " in output
    assert "Liveness check, timestamp:" in output


# Verifies the offline interval is used while the user is away and the shorter one once they appear
def test_polling_interval_follows_the_user_status(pm_module, psn_session, fake_clock, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_CHECK_INTERVAL", 180)
    monkeypatch.setattr(pm_module, "PSN_ACTIVE_CHECK_INTERVAL", 60)
    psn_session([presence_payload(status="offline"), presence_payload(status="online"), presence_payload(status="online")])

    run_monitor(pm_module)

    assert fake_clock.slept[:3] == [180, 60, 60]


# Verifies a profile that cannot be reached at startup stops the tool instead of monitoring nothing
def test_unreachable_profile_stops_startup(pm_module, psn_session, fake_clock, capsys):
    psn_session([psnawp_exceptions.PSNAWPNotFoundError("User not found")])

    with pytest.raises(SystemExit) as raised:
        pm_module.psn_monitor_user(USER_ID, "")

    assert raised.value.code == 1
    assert "does not know that PlayStation ID" in capsys.readouterr().out


# Verifies a status change reaches the webhook channel even when email alerts are off
def test_a_status_change_reaches_the_webhook_channel(pm_module, psn_session, fake_clock, monkeypatch, sent_webhooks, capsys):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", True)
    psn_session([presence_payload(status="offline"), presence_payload(status="online")])

    run_monitor(pm_module)

    assert [alert["type"] for alert in sent_webhooks] == ["status"]
    assert sent_webhooks[0]["title"].startswith(f"PSN user {USER_ID} is now online")


# Verifies a game change reaches the webhook channel on its own alert setting
def test_a_game_change_reaches_the_webhook_channel(pm_module, psn_session, fake_clock, monkeypatch, sent_webhooks):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_GAME_CHANGE_NOTIFICATION", True)
    psn_session([presence_payload(status="online"), presence_payload(status="online", game="Bloodborne")])

    run_monitor(pm_module)

    assert [alert["type"] for alert in sent_webhooks] == ["game"]
    assert "Bloodborne" in sent_webhooks[0]["title"]


# Verifies each channel is switched on by its own setting rather than by the other channel's
def test_the_channels_are_selected_independently(pm_module, psn_session, fake_clock, monkeypatch, sent_emails, sent_webhooks):
    monkeypatch.setattr(pm_module, "ACTIVE_INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_GAME_CHANGE_NOTIFICATION", True)
    psn_session([presence_payload(status="offline"), presence_payload(status="online"), presence_payload(status="online", game="Bloodborne")])

    run_monitor(pm_module)

    assert len(sent_emails) == 1
    assert [alert["type"] for alert in sent_webhooks] == ["game"]


# Verifies an error alert reaches both channels once, and is not repeated while the same failure persists
def test_an_error_alerts_both_channels_once(pm_module, psn_session, fake_clock, monkeypatch, sent_emails, sent_webhooks):
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_ERROR_NOTIFICATION", True)
    psn_session([
        presence_payload(status="offline"),
        psnawp_exceptions.PSNAWPAuthenticationError("Your npsso code has expired"),
        psnawp_exceptions.PSNAWPAuthenticationError("Your npsso code has expired"),
    ])

    run_monitor(pm_module)

    assert len(sent_emails) == 1
    assert [alert["type"] for alert in sent_webhooks] == ["error"]


# Verifies the channel that failed is retried on the next check while the one that succeeded is not resent
def test_only_the_failed_channel_is_retried(pm_module, psn_session, fake_clock, monkeypatch, sent_webhooks):
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_ERROR_NOTIFICATION", True)
    attempts = []
    monkeypatch.setattr(pm_module, "send_email", lambda *args, **kwargs: attempts.append("email") or 1)
    psn_session([
        presence_payload(status="offline"),
        psnawp_exceptions.PSNAWPAuthenticationError("Your npsso code has expired"),
        psnawp_exceptions.PSNAWPAuthenticationError("Your npsso code has expired"),
        psnawp_exceptions.PSNAWPAuthenticationError("Your npsso code has expired"),
    ])

    run_monitor(pm_module)

    # The webhook was delivered on the first failure, so only the email that failed is attempted again
    assert len(sent_webhooks) == 1
    assert len(attempts) == 3
