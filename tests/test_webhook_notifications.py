"""Tests for webhook delivery: the destination, the request each provider gets and the bounded retry."""

import pytest

import requests as req


DISCORD_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"
NTFY_URL = "https://ntfy.sh/private-topic-name"


# Stands in for one requests response with just the fields the delivery path reads
class FakeResponse:
    def __init__(self, status_code=204, headers=None, payload=None, text=""):
        self.status_code = status_code
        self.headers = headers if headers is not None else {}
        self.text = text
        self._payload = payload

    # Returns the canned JSON body, or refuses the way requests does when there is none
    def json(self):
        if self._payload is None:
            raise ValueError("no JSON body")
        return self._payload


# Records every webhook request instead of sending one, and replays scripted responses
class FakeWebhookSession:
    def __init__(self, responses=None):
        self.requests = []
        self.responses = list(responses) if responses is not None else [FakeResponse()]

    # Records one POST and returns the next scripted response, repeating the last one when the script runs out
    def post(self, url, **kwargs):
        self.requests.append(dict(kwargs, url=url))
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


@pytest.fixture
# Installs the recording session and returns a factory that scripts the responses it replays
def webhook_session(monkeypatch, pm_module):
    # Enclosed so a test can script the responses after the fixture was requested
    def install(responses=None):
        session = FakeWebhookSession(responses)
        monkeypatch.setattr(pm_module, "WEBHOOK_SESSION", session)
        return session

    return install


@pytest.fixture
# Turns on a working Discord destination, which most delivery tests start from
def discord_enabled(monkeypatch, pm_module):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", DISCORD_URL)
    monkeypatch.setattr(pm_module, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", True)
    return pm_module


@pytest.fixture
# Turns on a working ntfy destination
def ntfy_enabled(monkeypatch, pm_module):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", NTFY_URL)
    monkeypatch.setattr(pm_module, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", True)
    return pm_module


# Verifies delivery refuses to follow a redirect, since requests follows them by default and the destination
# is itself the credential: one Location header would hand the token and the payload to another host
def test_delivery_never_follows_a_redirect(discord_enabled, webhook_session):
    session = webhook_session()

    discord_enabled.post_webhook_request(json={"content": "hello"})

    assert session.requests[0]["allow_redirects"] is False


# Verifies only a complete private HTTPS destination is accepted
@pytest.mark.parametrize("url, accepted", [
    (DISCORD_URL, True),
    (NTFY_URL, True),
    ("https://ntfy.example.test/topic", True),
    ("http://discord.com/api/webhooks/1/token", False),
    ("https://discord.com", False),
    ("https://discord.com/", False),
    ("https://user:secret@ntfy.sh/topic", False),
    ("your_webhook_url", False),
    ("", False),
    (None, False),
    (12345, False),
])
def test_only_a_complete_https_destination_is_accepted(pm_module, url, accepted):
    assert pm_module.validate_webhook_url(url) is accepted


# Verifies a bare ntfy.sh topic name becomes a complete URL and anything unusable becomes nothing
@pytest.mark.parametrize("entered, expected", [
    ("private-topic-name", "https://ntfy.sh/private-topic-name"),
    ("Topic_1", "https://ntfy.sh/Topic_1"),
    (NTFY_URL, NTFY_URL),
    ("https://ntfy.example.test/topic", "https://ntfy.example.test/topic"),
    ("topic with spaces", ""),
    ("topic/with/slashes", ""),
    ("x" * 65, ""),
    ("", ""),
    (None, ""),
])
def test_an_ntfy_topic_name_is_expanded_to_a_url(pm_module, entered, expected):
    assert pm_module.normalize_ntfy_topic_url(entered) == expected


# Verifies the service is recognised from the URL shape, and that an unknown host stays unrecognised
@pytest.mark.parametrize("url, provider", [
    (DISCORD_URL, "discord"),
    ("https://canary.discord.com/api/v10/webhooks/1/token", "discord"),
    ("https://discordapp.com/api/webhooks/1/token", "discord"),
    (NTFY_URL, "ntfy"),
    ("https://ntfy.example.test/topic", ""),
    ("https://discord.com/api/webhooks/1/token/extra/parts", ""),
    ("https://example.test/hook", ""),
])
def test_the_service_is_detected_from_the_url(pm_module, url, provider):
    assert pm_module.detect_webhook_provider(url) == provider


# Verifies an unsupported provider name is rejected rather than quietly treated as one of the two
@pytest.mark.parametrize("configured, normalized", [("discord", "discord"), ("  NTFY ", "ntfy"), ("slack", ""), ("", ""), (12345, "")])
def test_only_the_two_supported_providers_normalize(pm_module, configured, normalized):
    assert pm_module.normalized_webhook_provider(configured) == normalized


# Verifies the display name falls back to the configured text, so a typo is visible in the report
def test_an_unsupported_provider_is_still_named_in_output(pm_module):
    assert pm_module.webhook_provider_display_name("discord") == "Discord"
    assert pm_module.webhook_provider_display_name("ntfy") == "ntfy"
    assert pm_module.webhook_provider_display_name("slack") == "slack"


# Verifies the master switch overrides every individual alert setting
def test_the_master_switch_turns_every_alert_off(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_GAME_CHANGE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_ERROR_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", False)

    assert [pm_module.webhook_event_enabled(name) for name in ("status", "game", "error")] == [False, False, False]

    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    assert [pm_module.webhook_event_enabled(name) for name in ("status", "game", "error")] == [True, True, True]


# Verifies a disabled alert type is recorded as a debug trace, since it repeats on every notification
def test_a_disabled_alert_type_is_traced_in_debug_only(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(pm_module, "DEBUG_MODE", False)

    assert pm_module.send_webhook("alert", "body", "status") == 1
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(pm_module, "DEBUG_MODE", True)

    assert pm_module.send_webhook("alert", "body", "status") == 1

    output = capsys.readouterr().out
    assert "Webhook delivery: outcome=skipped, type=status, reason=alerts are disabled" in output


# Verifies an alert type nothing defines cannot switch itself on
def test_an_unknown_alert_type_is_never_enabled(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)

    assert pm_module.webhook_event_enabled("trophies") is False


# Verifies DELIVERY_CONFIRMATIONS drops the delivery line without turning the rest of verbose mode off
def test_delivery_confirmations_can_be_turned_off(pm_module, monkeypatch, discord_enabled, webhook_session, capsys):
    webhook_session()
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(pm_module, "DELIVERY_CONFIRMATIONS", False)

    assert pm_module.send_webhook("PSN user is now online", "body text", "status") == 0

    assert "Webhook sent through" not in capsys.readouterr().out


# Verifies the Discord payload carries the alert, disables mentions and sends the colour as a number
def test_the_discord_payload_carries_the_alert_and_disables_mentions(pm_module, discord_enabled, webhook_session):
    session = webhook_session()

    assert pm_module.send_webhook("PSN user is now online", "body text", "status") == 0

    payload = session.requests[0]["json"]
    assert payload["allowed_mentions"] == {"parse": []}
    assert payload["username"] == "PSN Monitor"
    embed = payload["embeds"][0]
    assert embed["title"] == "PSN user is now online"
    assert embed["description"] == "body text"
    assert embed["color"] == pm_module.WEBHOOK_EVENT_COLORS["status"]
    assert embed["footer"]["text"] == f"PSN Monitor v{pm_module.VERSION}"


# Verifies a template that asks for mentions cannot re-enable them
def test_a_template_cannot_re_enable_mentions(pm_module, discord_enabled, webhook_session, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_TEMPLATE", {"content": "@everyone {title}", "allowed_mentions": {"parse": ["everyone"]}})
    session = webhook_session()

    assert pm_module.send_webhook("alert", "body", "status") == 0

    assert session.requests[0]["json"]["allowed_mentions"] == {"parse": []}


# Verifies an empty display name or avatar is left out, so Discord applies the webhook's own defaults
def test_an_empty_name_or_avatar_is_omitted(pm_module, discord_enabled, webhook_session, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_USERNAME", "")
    monkeypatch.setattr(pm_module, "WEBHOOK_AVATAR_URL", "")
    session = webhook_session()

    pm_module.send_webhook("alert", "body", "status")

    payload = session.requests[0]["json"]
    assert "username" not in payload
    assert "avatar_url" not in payload


# Verifies ntfy receives the body as a plain text message with the subject as its title
def test_the_ntfy_request_sends_a_native_message(pm_module, ntfy_enabled, webhook_session):
    session = webhook_session()

    assert pm_module.send_webhook("PSN user is now online", "body text", "status") == 0

    request = session.requests[0]
    assert request["data"] == b"body text"
    assert request["params"] == {"title": "PSN user is now online"}
    assert request["headers"]["Content-Type"] == "text/plain; charset=utf-8"
    assert "json" not in request


# Verifies an ntfy access token is sent as Bearer authentication and never appears in the topic URL
def test_an_ntfy_token_is_sent_as_bearer_authentication(pm_module, ntfy_enabled, webhook_session, monkeypatch):
    monkeypatch.setattr(pm_module, "NTFY_ACCESS_TOKEN", "  tk_a_real_looking_token  ")
    session = webhook_session()

    pm_module.send_webhook("alert", "body", "status")

    assert session.requests[0]["headers"]["Authorization"] == "Bearer tk_a_real_looking_token"
    assert session.requests[0]["url"] == NTFY_URL


# Verifies a token that already carries a scheme is refused rather than sent twice over
@pytest.mark.parametrize("token", ["Bearer tk_value", "basic dXNlcjpwYXNz", "tk_value\nX-Header: injected"])
def test_a_token_with_a_scheme_or_line_break_is_refused(pm_module, monkeypatch, token):
    monkeypatch.setattr(pm_module, "NTFY_ACCESS_TOKEN", token)

    assert pm_module.validate_webhook_headers("ntfy") is not None


# Verifies custom headers reach the request and the shipped user agent fills in when none was configured
def test_custom_headers_reach_the_request(pm_module, discord_enabled, webhook_session, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_HEADERS", {"X-Priority": "5", "X-Title": "{title}"})
    session = webhook_session()

    pm_module.send_webhook("alert title", "body", "status")

    headers = session.requests[0]["headers"]
    assert headers["X-Priority"] == "5"
    assert headers["X-Title"] == "alert title"
    assert headers["User-Agent"] == f"PSNMonitor/{pm_module.VERSION}"


# Verifies a configured user agent is kept instead of being replaced
def test_a_configured_user_agent_is_kept(pm_module, discord_enabled, webhook_session, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_HEADERS", {"user-agent": "MyIntegration/2.0"})
    session = webhook_session()

    pm_module.send_webhook("alert", "body", "status")

    headers = session.requests[0]["headers"]
    assert headers["user-agent"] == "MyIntegration/2.0"
    assert "User-Agent" not in headers


# Verifies unusable header mappings are named rather than sent
@pytest.mark.parametrize("headers, fragment", [
    ("not a mapping", "must be a dictionary"),
    ({"Bad Header": "value"}, "invalid HTTP header name"),
    ({"X-Tag": "a", "x-tag": "b"}, "duplicate case-insensitive"),
    ({"X-Tag": 5}, "must be a string"),
    ({"X-Tag": "value\r\nX-Injected: 1"}, "must not contain line breaks"),
])
def test_an_unusable_header_mapping_is_named(pm_module, monkeypatch, headers, fragment):
    monkeypatch.setattr(pm_module, "WEBHOOK_HEADERS", headers)

    assert fragment in pm_module.validate_webhook_headers("discord")


# Verifies a header value that only becomes dangerous after substitution is still refused
def test_a_placeholder_cannot_smuggle_a_second_header(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_HEADERS", {"X-Title": "{title}"})
    values = pm_module.build_webhook_values("first line\nX-Injected: 1", "body", "status")
    values["title"] = "first line\nX-Injected: 1"

    with pytest.raises(ValueError, match="line breaks"):
        pm_module.build_webhook_headers("discord", values)


# Verifies the alert title and body are bounded before either provider sees them
def test_an_over_long_alert_is_trimmed_for_discord(pm_module):
    values = pm_module.build_webhook_values("t" * 500, "d" * 6000, "status")

    assert len(values["title"]) == pm_module.WEBHOOK_EMBED_TITLE_LIMIT
    assert len(values["description"]) == pm_module.WEBHOOK_EMBED_DESCRIPTION_LIMIT


# Verifies an over-long ntfy message is trimmed to whole characters within the byte limit
def test_an_over_long_ntfy_message_is_trimmed_to_whole_characters(pm_module):
    _title, message = pm_module.build_ntfy_webhook_message("alert", "é" * 4000)

    encoded = message.encode("utf-8")
    assert len(encoded) <= pm_module.NTFY_MESSAGE_LIMIT_BYTES
    assert message.endswith(pm_module.NTFY_TRUNCATION_SUFFIX)
    assert encoded.decode("utf-8") == message


# Verifies a message that fits is left exactly as it was
def test_a_message_that_fits_is_untouched(pm_module):
    assert pm_module.truncate_utf8_bytes("short", 100, "...") == "short"


# Verifies a title with a line break cannot break the embed or the ntfy header it is sent in
def test_a_title_never_carries_a_line_break(pm_module):
    values = pm_module.build_webhook_values("first\nsecond", "body", "status")
    title, _message = pm_module.build_ntfy_webhook_message("first\nsecond", "body")

    assert values["title"] == "first second"
    assert title == "first second"


# Verifies a secret that reached the alert text is redacted before it leaves the process
def test_a_secret_in_the_alert_is_redacted_before_delivery(pm_module, discord_enabled, webhook_session, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "npsso-secret-value-1234")
    session = webhook_session()

    pm_module.send_webhook("alert", "The token npsso-secret-value-1234 expired", "status")

    assert "npsso-secret-value-1234" not in session.requests[0]["json"]["embeds"][0]["description"]


# Verifies the configured transformations are applied to the values the template and headers share
def test_transformations_are_applied_to_the_alert_values(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_TRANSFORMS", [("title", "upper"), ("description", "replace", "**", "")])

    values = pm_module.build_webhook_values("online", "**bold** text", "status")

    assert values["title"] == "ONLINE"
    assert values["description"] == "bold text"


# Verifies a transformation cannot reach a private attribute or an unknown method
@pytest.mark.parametrize("transform, fragment", [
    (("title", "__class__"), "unsupported string method"),
    (("title", "explode"), "unsupported string method"),
    (("title",), "field name and a string method name"),
    ("title.upper", "field name and a string method name"),
])
def test_an_unsafe_transformation_is_refused(pm_module, monkeypatch, transform, fragment):
    monkeypatch.setattr(pm_module, "WEBHOOK_TRANSFORMS", [transform])

    assert fragment in pm_module.validate_webhook_customization("discord")


# Verifies an avatar that is not a complete HTTPS link is refused before anything is sent
def test_an_unusable_avatar_is_refused(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_AVATAR_URL", "http://example.test/avatar.png")

    assert "WEBHOOK_AVATAR_URL" in pm_module.validate_webhook_customization("discord")


# Verifies delivery refuses before the first request when a setting cannot be used
@pytest.mark.parametrize("setting, value", [
    ("WEBHOOK_URL", "your_webhook_url"),
    ("WEBHOOK_PROVIDER", "slack"),
    ("WEBHOOK_AVATAR_URL", "not-a-url"),
    ("WEBHOOK_HEADERS", {"Bad Header": "value"}),
])
def test_an_unusable_setting_stops_delivery_before_the_request(pm_module, discord_enabled, webhook_session, monkeypatch, capsys, setting, value):
    monkeypatch.setattr(pm_module, setting, value)
    session = webhook_session()

    assert pm_module.send_webhook("alert", "body", "status") == 1

    assert session.requests == []
    assert "* Error:" in capsys.readouterr().out


# Verifies a disabled alert type is skipped, and that a forced send ignores the alert settings
def test_a_disabled_alert_is_skipped_unless_it_is_forced(pm_module, discord_enabled, webhook_session, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", False)
    session = webhook_session()

    assert pm_module.send_webhook("alert", "body", "status") == 1
    assert session.requests == []

    assert pm_module.send_webhook("alert", "body", "status", force=True) == 0
    assert len(session.requests) == 1


# Verifies every delivery refuses redirects and carries the shared deadline
def test_delivery_refuses_redirects_and_carries_the_deadline(pm_module, discord_enabled, webhook_session):
    session = webhook_session()

    pm_module.send_webhook("alert", "body", "status")

    request = session.requests[0]
    assert request["allow_redirects"] is False
    assert request["timeout"] == pm_module.WEBHOOK_TIMEOUT_SECONDS


# Verifies the destination is checked again inside the request, so a reload cannot redirect a live delivery
def test_the_destination_is_rechecked_inside_the_request(pm_module, discord_enabled, webhook_session, monkeypatch):
    webhook_session()
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", "http://evil.example.test/hook")

    with pytest.raises(req.exceptions.InvalidURL):
        pm_module.post_webhook_request(json={})


# Verifies a rate limit waits the delay the service asked for, then delivers on the second attempt
def test_a_rate_limit_waits_the_requested_delay_then_retries(pm_module, discord_enabled, webhook_session):
    session = webhook_session([FakeResponse(429, {"Retry-After": "2"}), FakeResponse(204)])
    slept = []

    assert pm_module.send_webhook("alert", "body", "status", sleeper=slept.append) == 0

    assert slept == [2.0]
    assert len(session.requests) == 2


# Verifies an untrusted retry delay is bounded instead of being waited out in full
@pytest.mark.parametrize("retry_after, waited", [("900", 5.0), ("-30", 0.0), ("not a number", 1.0), ("", 1.0)])
def test_an_untrusted_retry_delay_is_bounded(pm_module, discord_enabled, webhook_session, retry_after, waited):
    webhook_session([FakeResponse(429, {"Retry-After": retry_after}), FakeResponse(204)])
    slept = []

    pm_module.send_webhook("alert", "body", "status", sleeper=slept.append)

    assert slept == [waited]


# Verifies the JSON body is read when the service reports its delay there instead of in a header
def test_a_retry_delay_in_the_body_is_used(pm_module, discord_enabled, webhook_session):
    webhook_session([FakeResponse(429, {}, {"retry_after": 3}), FakeResponse(204)])
    slept = []

    pm_module.send_webhook("alert", "body", "status", sleeper=slept.append)

    assert slept == [3.0]


# Verifies a server fault is retried once and a rejected request is not retried at all
@pytest.mark.parametrize("status, attempts", [(500, 2), (503, 2), (400, 1), (401, 1), (404, 1)])
def test_only_a_server_fault_is_retried(pm_module, discord_enabled, webhook_session, status, attempts):
    session = webhook_session([FakeResponse(status), FakeResponse(status)])

    assert pm_module.send_webhook("alert", "body", "status", sleeper=lambda seconds: None) == 1

    assert len(session.requests) == attempts


# Verifies a network failure is retried once and then reported through the shared recovery renderer
def test_a_network_failure_is_retried_once_then_reported(pm_module, discord_enabled, monkeypatch, capsys):
    attempts = []

    # Fails the way requests does when the host cannot be reached
    def failing_post(url, **kwargs):
        attempts.append(url)
        raise req.exceptions.ConnectionError("connection refused")

    monkeypatch.setattr(pm_module, "WEBHOOK_SESSION", type("Session", (), {"post": staticmethod(failing_post)}))

    assert pm_module.send_webhook("alert", "body", "status", sleeper=lambda seconds: None) == 1

    assert len(attempts) == pm_module.WEBHOOK_MAX_ATTEMPTS
    output = capsys.readouterr().out
    assert "* Error: The webhook service could not be reached" in output
    assert "To fix:" in output


# Verifies the failure the service reported is classified rather than printed as a bare line
def test_a_rejected_delivery_is_classified(pm_module, discord_enabled, webhook_session, capsys):
    webhook_session([FakeResponse(404, text="Unknown Webhook")])

    assert pm_module.send_webhook("alert", "body", "status") == 1

    output = capsys.readouterr().out
    assert "* Error:" in output
    assert "To fix:" in output


# Verifies unavailable automatic channels make no attempt or status line
def test_unavailable_channels_are_silent(pm_module, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "")
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", "")
    monkeypatch.setattr(pm_module, "send_email", lambda *args, **kwargs: calls.append("email"))
    monkeypatch.setattr(pm_module, "send_webhook", lambda *args, **kwargs: calls.append("webhook"))
    assert pm_module.send_notification_channels("error", "Subject", "Body", email_enabled=True, webhook_enabled=True) == (False, False)
    assert calls == []
    assert capsys.readouterr().out == ""


# Verifies the two channels are switched on independently and each reports its own delivery
def test_each_channel_reports_its_own_delivery(pm_module, monkeypatch, capsys, discord_enabled):
    monkeypatch.setattr(pm_module, "send_email", lambda *args, **kwargs: 1)
    monkeypatch.setattr(pm_module, "send_webhook", lambda *args, **kwargs: 0)

    delivered = pm_module.send_notification_channels("status", "subject", "body", email_enabled=True, webhook_enabled=True)

    assert delivered == (False, True)
    output = capsys.readouterr().out
    assert "Sending email notification to alerts@example.test" in output
    assert "Sending webhook notification" in output


# Verifies a channel that was not asked for is left alone
def test_a_channel_that_is_off_is_not_contacted(pm_module, monkeypatch):
    calls = []
    monkeypatch.setattr(pm_module, "send_email", lambda *args, **kwargs: calls.append("email") or 0)
    monkeypatch.setattr(pm_module, "send_webhook", lambda *args, **kwargs: calls.append("webhook") or 0)

    assert pm_module.send_notification_channels("status", "subject", "body", email_enabled=False, webhook_enabled=False) == (False, False)

    assert calls == []


# Verifies the webhook channel falls back to its own alert settings when the caller names no preference
def test_the_webhook_channel_falls_back_to_its_own_settings(pm_module, monkeypatch, discord_enabled):
    calls = []
    monkeypatch.setattr(pm_module, "send_email", lambda *args, **kwargs: 0)
    monkeypatch.setattr(pm_module, "send_webhook", lambda *args, **kwargs: calls.append(args[2]) or 0)
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_GAME_CHANGE_NOTIFICATION", True)

    pm_module.send_notification_channels("game", "subject", "body")

    assert calls == ["game"]


# Verifies a private webhook URL is redacted wherever it appears in reported text
def test_a_private_destination_is_redacted_in_reported_text(pm_module):
    sanitized = pm_module.sanitize_error_text(f"POST {DISCORD_URL} failed")

    assert "aVeryLongWebhookTokenValue" not in sanitized
    assert "<redacted>" in sanitized


# Verifies a token carried in a query string is redacted too
def test_a_token_in_a_query_string_is_redacted(pm_module):
    sanitized = pm_module.sanitize_error_text("https://ntfy.example.test/topic?auth=tk_secret_value")

    assert "tk_secret_value" not in sanitized


# Verifies the destination is reported by host only, so diagnostics never carry the private path
def test_diagnostics_name_the_host_without_the_private_path(pm_module, discord_enabled):
    assert pm_module.webhook_destination_host() == "discord.com"
    assert pm_module.webhook_destination_host("not a url") == "unknown host"
