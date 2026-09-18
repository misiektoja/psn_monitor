"""Tests for presence parsing, platform labels and title normalization."""

import pytest

from conftest import presence_payload


# Verifies a complete presence payload is flattened into the fields the monitor works with
def test_full_presence_is_flattened(pm_module):
    payload = presence_payload(status="online", platform_code="PS5", game="Bloodborne", launch_platform="ps4", last_online="2026-01-01T10:00:00Z")

    parsed = pm_module.parse_presence(payload)

    assert parsed == {"status": "online", "platform": "PS5", "last_online": "2026-01-01T10:00:00Z", "availability": "availableToPlay", "game_name": "Bloodborne", "launch_platform": "ps4"}


# Verifies a user who is not in a game reports no title rather than failing
def test_presence_without_a_game_reports_no_title(pm_module):
    parsed = pm_module.parse_presence(presence_payload(status="offline"))

    assert parsed["game_name"] is None
    assert parsed["launch_platform"] is None


# Verifies an absent gameTitleInfoList is accepted, since PSN omits it for offline users
def test_missing_game_title_list_is_accepted(pm_module):
    payload = presence_payload(status="offline")
    del payload["basicPresence"]["gameTitleInfoList"]

    assert pm_module.parse_presence(payload)["game_name"] is None


@pytest.mark.parametrize("payload,expected_field", [
    ("not a dict", "top-level"),
    ({}, "basicPresence"),
    ({"basicPresence": []}, "basicPresence"),
    ({"basicPresence": {"primaryPlatformInfo": None}}, "primaryPlatformInfo"),
    ({"basicPresence": {"primaryPlatformInfo": {}, "gameTitleInfoList": {}}}, "gameTitleInfoList"),
    ({"basicPresence": {"primaryPlatformInfo": {}, "gameTitleInfoList": ["oops"]}}, "gameTitleInfoList[0]"),
])
# Verifies every unexpected response shape is tagged as malformed and names the offending field
def test_unexpected_shapes_raise_a_tagged_error(pm_module, payload, expected_field):
    with pytest.raises(pm_module.PsnMalformedResponse) as raised:
        pm_module.parse_presence(payload)

    assert expected_field in str(raised.value)


# Verifies the malformed-response error stays a ValueError, which the surrounding code relies on
def test_malformed_response_is_a_value_error(pm_module):
    assert issubclass(pm_module.PsnMalformedResponse, ValueError)


@pytest.mark.parametrize("platform_code,expected", [
    ("PS5", "PlayStation 5"),
    ("ps4", "PlayStation 4"),
    (" PS3 ", "PlayStation 3"),
    ("PS_VITA", "PlayStation Vita"),
    ("MOBILE_APP", "PlayStation App (mobile)"),
])
# Verifies known platform codes are shown with their full product names
def test_known_platform_codes_get_readable_labels(pm_module, platform_code, expected):
    assert pm_module.format_platform_display(platform_code) == expected


# Verifies a platform PSN adds later is still shown instead of being dropped
def test_unknown_platform_code_is_preserved(pm_module):
    assert pm_module.format_platform_display("ps6_pro") == "PS6 PRO"


# Verifies an absent platform produces an empty label so nothing is printed
def test_absent_platform_renders_as_empty(pm_module):
    assert pm_module.format_platform_display(None) == ""
    assert pm_module.format_platform_display("") == ""


@pytest.mark.parametrize("raw,expected", [
    ("Marvel’s Spider-Man", "Marvel's Spider-Man"),
    ("Ratchet & Clank™", "Ratchet & Clank"),
    ("Gran Turismo® 7", "Gran Turismo 7"),
    ("Horizon Forbidden West", "Horizon Forbidden West"),
    ("Uncharted   4", "Uncharted 4"),
    ("  Returnal  ", "Returnal"),
    ("God of War–Ragnar", "God of War-Ragnar"),
    ("To be continued…", "To be continued..."),
])
# Verifies game titles are normalized to ASCII so logs, CSV rows and emails stay readable everywhere
def test_game_titles_are_normalized_to_ascii(pm_module, raw, expected):
    assert pm_module.normalize_ascii(raw) == expected


# Verifies a non-string title is returned untouched rather than crashing the poll
def test_non_string_titles_pass_through(pm_module):
    assert pm_module.normalize_ascii(None) is None
    assert pm_module.normalize_ascii(42) == 42
