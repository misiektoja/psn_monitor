"""Tests for the HTML notification body, its Discord markdown form and its match with the plain text."""

import difflib
import html as html_module
import json
import os
import re
from pathlib import Path

import pytest

from conftest import LoopFinished, presence_payload

USER_ID = "misiektoja"


# Reduces one HTML body back to the text it represents, independently of the module's own converter
def html_to_text(body_html):
    text = re.sub(r"(?is)</?(?:html|head|body)\s*>", "", str(body_html or ""))
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    return html_module.unescape(text)


# Returns the unified diff between the plain body and the text the HTML body reduces to, empty when they match
def structural_diff(body, body_html):
    reduced = html_to_text(body_html)
    if reduced == body:
        return ""
    return "\n".join(difflib.unified_diff(body.split("\n"), reduced.split("\n"), fromfile="plain", tofile="html-reduced", lineterm=""))


@pytest.fixture
# Collects every alert the monitoring loop tries to send, without delivering any of them
def captured_alerts(pm_module, monkeypatch):
    captured = []

    def fake_send(notification_type, subject, body, body_html="", **kwargs):
        captured.append({"type": notification_type, "subject": subject, "body": body, "body_html": body_html, "webhook_body": kwargs.get("webhook_body") or body, "discord": pm_module.html_body_to_discord_markdown(kwargs.get("webhook_body_html") or body_html)})
        return bool(kwargs.get("email_enabled")), bool(kwargs.get("webhook_enabled"))

    monkeypatch.setattr(pm_module, "send_notification_channels", fake_send)
    return captured


@pytest.fixture(autouse=True)
# Keeps the state file and the log inside the test directory
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
# Every alert a presence timeline covering status changes and game changes produces
def timeline_alerts(pm_module, psn_session, fake_clock, monkeypatch, captured_alerts, capsys):
    monkeypatch.setattr(pm_module, "ACTIVE_INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "GAME_CHANGE_NOTIFICATION", True)
    psn_session([
        presence_payload(status="offline"),
        presence_payload(status="online"),
        presence_payload(status="online", game="Bloodborne", launch_platform="PS5"),
        presence_payload(status="online", game="Elden Ring", launch_platform="PS5"),
        presence_payload(status="online"),
        presence_payload(status="offline"),
    ])
    with pytest.raises(LoopFinished):
        pm_module.psn_monitor_user(USER_ID, "")
    capsys.readouterr()
    return captured_alerts


# Verifies a value taken from PlayStation Network is escaped before it reaches the HTML body
def test_untrusted_text_is_escaped(pm_module):
    assert pm_module.html_text("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert pm_module.html_text("line\nbreak") == "line<br>break"
    assert pm_module.escape_html_attr('" onload="x') == "&quot; onload=&quot;x"


# Verifies a crafted online ID or game title cannot inject markup through the bolded subject
def test_a_crafted_name_cannot_inject_markup(pm_module):
    assert pm_module.psn_user_html("<img src=x>") == "<b>&lt;img src=x&gt;</b>"
    assert pm_module.psn_game_html("<b>Game</b>") == "<b>&lt;b&gt;Game&lt;/b&gt;</b>"


# Verifies a bare URL in an alert becomes a link while one already inside an attribute is left alone
def test_bare_urls_are_linked_once(pm_module):
    assert pm_module.html_autolink_urls("Guide: https://example.test/a") == 'Guide: <a href="https://example.test/a">https://example.test/a</a>'
    assert pm_module.html_autolink_urls('<a href="https://example.test/a">x</a>') == '<a href="https://example.test/a">x</a>'


# Verifies the Discord body carries the email's emphasis and links instead of raw markup
def test_discord_markdown_mirrors_the_html_body(pm_module):
    body_html = pm_module.html_email_body('PSN user <b>misiektoja</b> is now <b>online</b><br><br>Guide: <a href="https://example.test/a">docs</a>')

    assert pm_module.html_body_to_discord_markdown(body_html) == "PSN user **misiektoja** is now **online**\n\nGuide: [docs](https://example.test/a)"


# Verifies a link whose label repeats its destination is left bare, which Discord turns into a link itself
def test_a_self_labeled_link_stays_bare_in_discord(pm_module):
    assert pm_module.html_body_to_discord_markdown('<a href="https://example.test/a">https://example.test/a</a>') == "https://example.test/a"


# Verifies the failure alert bolds its summary and the two values that say how bad the outage is
def test_the_failure_alert_bolds_its_summary_and_outage_fields(pm_module):
    advice = pm_module.make_recovery_advice("psn.rate_limited", "PlayStation Network is unreachable", "Retry later", True)

    rendered = pm_module.recovery_alert_body_html(advice, 60, failed_checks=2, failing_since=1700000000)

    assert rendered.startswith("<html><head></head><body><b>PlayStation Network is unreachable</b><br><br>")
    assert "Failed checks in a row: <b>2</b>" in rendered
    assert "Failing since: <b>" in rendered
    # The retry delay is configured rather than observed, so it carries no emphasis
    assert "Next retry in: 1 minute" in rendered
    assert rendered.endswith("</body></html>")


# Verifies the webhook copy of an alert leaves out the timestamp the email carries
def test_the_webhook_body_has_no_timestamp(pm_module):
    advice = pm_module.make_recovery_advice("psn.rate_limited", "PlayStation Network is unreachable", "Retry later", True)

    assert "Timestamp: " not in pm_module.recovery_alert_body_html(advice, 60, timestamp=False)
    assert "Timestamp: " in pm_module.recovery_alert_body_html(advice, 60)


# Verifies the timeline reaches both alert types, so the structural check is not silently narrow
def test_the_timeline_covers_status_and_game_alerts(timeline_alerts):
    assert {alert["type"] for alert in timeline_alerts} == {"status", "game"}


# Verifies every alert carries an HTML body next to its plain one
def test_every_alert_has_an_html_body(timeline_alerts):
    assert [alert["subject"] for alert in timeline_alerts if not alert["body_html"]] == []


# Verifies each HTML body reduces back to its plain body, so no line break was added or lost
def test_html_bodies_match_the_plain_text(timeline_alerts):
    mismatches = [f"{alert['type']}: {alert['subject']}\n{structural_diff(alert['body'], alert['body_html'])}" for alert in timeline_alerts if structural_diff(alert["body"], alert["body_html"])]

    assert mismatches == []


# Verifies every HTML body is one complete document, so no fragment reaches a mail client unwrapped
def test_html_bodies_are_complete_documents(timeline_alerts):
    for alert in timeline_alerts:
        assert alert["body_html"].startswith("<html><head></head><body>")
        assert alert["body_html"].endswith("</body></html>")


# Verifies the Discord body keeps the wording the ntfy body carries once its markers are removed
def test_discord_bodies_keep_the_plain_wording(timeline_alerts):
    for alert in timeline_alerts:
        stripped = re.sub(r"\[([^\]]*)\]\((?:[^)]*)\)", r"\1", alert["discord"]).replace("**", "").replace("*", "")

        assert stripped == alert["webhook_body"].strip()


# Verifies the online ID and the game title are the bold subjects of the alerts that name them
def test_alerts_bold_the_entities_they_name(timeline_alerts):
    for alert in timeline_alerts:
        assert f"<b>{USER_ID}</b>" in alert["body_html"]
    game_alerts = [alert for alert in timeline_alerts if alert["type"] == "game"]

    assert game_alerts
    assert any("<b>Bloodborne</b>" in alert["body_html"] for alert in game_alerts)


# Writes the captured alerts as JSON when PREVIEW_ALERTS_JSON names a destination, so a preview tool can render them
@pytest.mark.skipif(not os.environ.get("PREVIEW_ALERTS_JSON"), reason="set PREVIEW_ALERTS_JSON to dump the alerts")
def test_dump_the_alerts_for_a_preview(timeline_alerts):
    Path(os.environ["PREVIEW_ALERTS_JSON"]).write_text(json.dumps(timeline_alerts, indent=2), encoding="utf-8")
