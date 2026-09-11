"""Tests for SMTP validation and the message the tool actually hands to the server."""

import email
import smtplib
from email.header import decode_header, make_header

import pytest


# Stands in for smtplib.SMTP and records everything the tool asks it to do
class FakeSMTP:
    last = None

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_args = None
        self.sent = None
        self.quit_called = False
        FakeSMTP.last = self

    # Records that the connection was upgraded to TLS
    def starttls(self, context=None):
        self.started_tls = True
        self.tls_context = context

    # Records the credentials the tool authenticated with
    def login(self, user, password):
        self.login_args = (user, password)

    # Records the delivered message
    def sendmail(self, sender, receiver, message):
        self.sent = {"sender": sender, "receiver": receiver, "message": message}

    # Records that the session was closed
    def quit(self):
        self.quit_called = True


@pytest.fixture
# Replaces the SMTP client with the recording double
def smtp_double(monkeypatch, pm_module):
    FakeSMTP.last = None
    monkeypatch.setattr(pm_module.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


# Verifies a valid notification is delivered over TLS to the configured recipient
def test_notification_is_delivered_over_tls(pm_module, smtp_double):
    assert pm_module.send_email("PSN user is now online", "body text", "", True) == 0

    delivery = smtp_double.last
    assert delivery.host == "smtp.example.test"
    assert delivery.port == 587
    assert delivery.started_tls is True
    assert delivery.login_args == ("monitor@example.test", "not-a-real-password")
    assert delivery.sent["receiver"] == "alerts@example.test"
    assert delivery.quit_called is True


# Verifies a plain SMTP session skips the TLS upgrade when the operator turned SSL off
def test_plain_session_skips_the_tls_upgrade(pm_module, smtp_double):
    assert pm_module.send_email("subject", "body", "", False) == 0

    assert smtp_double.last.started_tls is False


# Verifies both message parts are sent as UTF-8, so a game title with accents survives delivery
def test_message_carries_both_parts_as_utf8(pm_module, smtp_double):
    pm_module.send_email("PSN user plays Pokémon", "plain body with Pokémon", "<b>html body with Pokémon</b>", True)

    message = email.message_from_string(smtp_double.last.sent["message"])
    payload_types = [part.get_content_type() for part in message.walk() if part.get_content_maintype() == "text"]
    assert payload_types == ["text/plain", "text/html"]
    decoded = []
    for part in message.walk():
        if part.get_content_maintype() != "text":
            continue
        payload = part.get_payload(decode=True)
        assert isinstance(payload, bytes)
        decoded.append(payload.decode("utf-8"))
    assert "Pokémon" in decoded[0]
    assert "Pokémon" in decoded[1]
    assert "Pokémon" in str(make_header(decode_header(message["Subject"])))


# Verifies an ASCII body is still declared and encoded as UTF-8, so a later accented character in the same
# thread does not arrive in a different encoding than the rest of the message
def test_an_ascii_body_is_still_declared_utf8(pm_module, smtp_double):
    pm_module.send_email("subject", "plain body", "<b>html body</b>", True)

    message = email.message_from_string(smtp_double.last.sent["message"])
    parts = [part for part in message.walk() if part.get_content_maintype() == "text"]
    assert [part.get_content_charset() for part in parts] == ["utf-8", "utf-8"]
    assert [part["Content-Transfer-Encoding"] for part in parts] == ["base64", "base64"]
    assert [part.get_payload(decode=True) for part in parts] == [b"plain body", b"<b>html body</b>"]


# Verifies an IP address is accepted as the SMTP host, which a self-hosted relay commonly uses
def test_ip_address_host_is_accepted(pm_module, smtp_double, monkeypatch):
    monkeypatch.setattr(pm_module, "SMTP_HOST", "192.0.2.25")

    assert pm_module.send_email("subject", "body", "", True) == 0


@pytest.mark.parametrize("setting,value", [
    ("SMTP_HOST", "not a host"),
    ("SMTP_PORT", 0),
    ("SMTP_PORT", 70000),
    ("SMTP_PORT", "not a port"),
    ("SENDER_EMAIL", "not-an-email"),
    ("RECEIVER_EMAIL", "not-an-email"),
    ("SMTP_USER", "your_smtp_user"),
    ("SMTP_USER", ""),
    ("SMTP_PASSWORD", "your_smtp_password"),
    ("SMTP_PASSWORD", ""),
])
# Verifies incomplete or placeholder SMTP settings are refused before any connection is attempted
def test_incomplete_settings_are_refused_without_connecting(pm_module, smtp_double, monkeypatch, setting, value):
    monkeypatch.setattr(pm_module, setting, value)

    assert pm_module.send_email("subject", "body", "", True) == 1
    assert smtp_double.last is None


# Verifies a message with nothing to say is refused rather than delivered empty
def test_empty_message_is_refused(pm_module, smtp_double):
    assert pm_module.send_email("subject", "", "", True) == 1
    assert pm_module.send_email("", "body", "", True) == 1
    assert smtp_double.last is None


# Verifies a failing SMTP server is reported as a failure instead of raising into the monitoring loop
def test_smtp_failures_are_reported_not_raised(pm_module, monkeypatch, capsys):
    # Refuses the connection the way an unreachable relay would
    def refuse(*args, **kwargs):
        raise smtplib.SMTPConnectError(421, "service not available")

    monkeypatch.setattr(pm_module.smtplib, "SMTP", refuse)

    assert pm_module.send_email("subject", "body", "", True) == 1
    assert "The SMTP server could not be reached" in capsys.readouterr().out


# Verifies the configured timeout reaches the SMTP client, so a hung relay cannot stall the poll loop
def test_timeout_is_passed_to_the_smtp_client(pm_module, smtp_double):
    pm_module.send_email("subject", "body", "", True, smtp_timeout=5)

    assert smtp_double.last.timeout == 5


# Verifies PSN-supplied names cannot carry terminal control sequences into a mail client
def test_control_sequences_are_removed_from_the_delivered_message(pm_module, smtp_double):
    assert pm_module.send_email("psn_monitor: Ghost\x1b[2J", "started playing Ghost\x07 of\r Tsushima", "", True) == 0

    message = email.message_from_string(smtp_double.last.sent["message"])
    subject = str(make_header(decode_header(message["Subject"])))
    payload = next(part for part in message.walk() if part.get_content_type() == "text/plain").get_payload(decode=True)
    assert isinstance(payload, bytes)
    body = payload.decode("utf-8")
    assert subject == "psn_monitor: Ghost"
    assert body == "started playing Ghost of Tsushima"


# Verifies a server that echoes the credential back cannot get it printed to the screen or the log
def test_delivery_errors_do_not_leak_the_smtp_password(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "aVeryLongSmtpPassword123")
    # Debug mode is the only setting that puts the raw server error on screen, so it is where the leak would show
    monkeypatch.setattr(pm_module, "DEBUG_MODE", True)

    # Rejects the login the way a relay quoting the offending credential would
    def reject(*args, **kwargs):
        raise smtplib.SMTPAuthenticationError(535, "rejected aVeryLongSmtpPassword123")

    monkeypatch.setattr(pm_module.smtplib, "SMTP", reject)

    assert pm_module.send_email("subject", "body", "", True) == 1

    printed = capsys.readouterr().out
    assert "aVeryLongSmtpPassword123" not in printed
    assert "<redacted>" in printed


# Verifies delivery is reported as an outcome, since the caller only announces the attempt
def test_the_delivery_outcome_is_reported_not_only_the_attempt(pm_module, monkeypatch, smtp_double, capsys):
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(pm_module, "DEBUG_MODE", True)

    assert pm_module.send_email("psn_monitor: test", "body", "", True) == 0

    printed = capsys.readouterr().out
    assert "SMTP delivery: host=smtp.example.test, port=587, starttls=True, timeout=15s, user=monitor@example.test" in printed
    assert "* Email delivered to alerts@example.test: 'psn_monitor: test'" in printed


# Verifies DELIVERY_CONFIRMATIONS drops the delivery line without turning the rest of verbose mode off
def test_delivery_confirmations_can_be_turned_off(pm_module, monkeypatch, smtp_double, capsys):
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(pm_module, "DELIVERY_CONFIRMATIONS", False)

    assert pm_module.send_email("psn_monitor: test", "body", "", True) == 0

    assert "Email delivered" not in capsys.readouterr().out


# Verifies a failed delivery is not reported as delivered
def test_a_failed_delivery_is_not_reported_as_delivered(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)

    # Refuses the connection the way an unreachable relay would
    def refuse(*args, **kwargs):
        raise smtplib.SMTPConnectError(421, "service not available")

    monkeypatch.setattr(pm_module.smtplib, "SMTP", refuse)

    assert pm_module.send_email("psn_monitor: test", "body", "", True) == 1
    assert "Email delivered" not in capsys.readouterr().out
