"""Offline tests for the one-shot profile report produced by -i / --info."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from psnawp_api import PSNAWP

from conftest import presence_payload

USER_ID = "misiektoja"


@pytest.fixture(autouse=True)
# Keeps the status file this mode reads and the log inside the test directory
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
# Keeps the auth probe offline, since the startup error paths call it before deciding what to report
def offline_auth_probe(monkeypatch, pm_module):
    monkeypatch.setattr(pm_module, "probe_npsso_auth_error", lambda npsso: None)


@pytest.fixture(autouse=True)
# Keeps a fixed terminal width so the recently played table renders identically everywhere
def fixed_terminal_width(monkeypatch, pm_module):
    monkeypatch.setattr(pm_module.shutil, "get_terminal_size", lambda fallback=(100, 24): SimpleNamespace(columns=100, lines=24))


# Builds one entry of the recently played games table
def title_stat(name, category="ps5_native_game", last_played=None, play_duration=None):
    return SimpleNamespace(name=name, category=SimpleNamespace(name=category), last_played_date_time=last_played, play_duration=play_duration)


# Builds one earned trophy
def trophy(name, trophy_type="GOLD", earned=True, earned_at=None, hidden=False):
    return SimpleNamespace(trophy_name=name, trophy_type=SimpleNamespace(name=trophy_type), earned=earned, earned_date_time=earned_at, hidden=hidden)


# Stands in for a PSNAWP user in the reporting mode, including the trophy and title endpoints
class FakeInfoUser:
    def __init__(self, presence, profile=None, friendship=None, titles=None, trophies_by_title=None, trophy_summary_value=None, title_stats_value=None):
        self.account_id = "1234567890"
        self.presence = presence
        self._profile = profile if profile is not None else {"aboutMe": "Hunting beasts", "isPlus": True, "languages": ["en", "pl"], "isOfficiallyVerified": False}
        self._friendship = friendship if friendship is not None else {"friendRelation": "friend", "mutualFriendsCount": 7}
        self._titles = titles or []
        self._trophies_by_title = trophies_by_title or {}
        self._trophy_summary = trophy_summary_value
        self._title_stats = title_stats_value or []
        self.title_stats_kwargs = None

    # Returns the canned presence payload
    def get_presence(self):
        return self.presence

    # Returns the canned profile document
    def profile(self):
        return self._profile

    # Returns the canned friendship document
    def friendship(self):
        return self._friendship

    # Returns the canned shareable profile link
    def get_shareable_profile_link(self):
        return {"shareUrl": "https://psn.example/misiektoja"}

    # Returns the account-wide trophy summary, or a per-title one the name resolver may ask for
    def trophy_summary(self, np_communication_id=None, platform=None):
        if np_communication_id is not None:
            raise LookupError("per-title summary unavailable")
        if self._trophy_summary is None:
            raise LookupError("trophy visibility is restricted")
        return self._trophy_summary

    # Returns the titles the account has trophies in
    def trophy_titles(self, limit=None):
        return list(self._titles)

    # Returns no trophy groups, which pushes the name resolver to the title list
    def trophy_groups(self, np_communication_id=None, platform=None):
        raise LookupError("trophy groups unavailable")

    # Returns the earned trophies recorded for one title
    def trophies(self, np_communication_id=None, platform=None, include_progress=False, trophy_group_id=None):
        if np_communication_id not in self._trophies_by_title:
            raise LookupError("no trophies for this title")
        return list(self._trophies_by_title[np_communication_id])

    # Returns the recently played games and records how they were requested
    def title_stats(self, limit=None, page_size=None):
        self.title_stats_kwargs = {"limit": limit, "page_size": page_size}
        return list(self._title_stats)


# Installs the PSNAWP double for the reporting mode
@pytest.fixture
def info_user(monkeypatch, pm_module):
    # Primes the module with one fake user and returns it
    def build(**kwargs):
        user = FakeInfoUser(**kwargs)
        client = PSNAWP("a" * 64)
        monkeypatch.setattr(client, "user", lambda online_id: user)
        monkeypatch.setattr(pm_module, "PSNAWP", lambda npsso: client)
        return user

    return build


# Verifies the report covers identity, status, platform, profile details and the shareable link
def test_report_covers_the_profile(pm_module, info_user, capsys):
    info_user(presence=presence_payload(status="online", platform_code="PS5", game="Bloodborne", launch_platform="ps4"))

    pm_module.get_user_info(USER_ID, include_trophies=False, show_recent_games=False)

    output = capsys.readouterr().out
    assert f"PlayStation ID:\t\t\t{USER_ID}" in output
    assert "PSN account ID:\t\t\t1234567890" in output
    assert "Status:\t\t\t\tONLINE" in output
    assert "Available to play:\t\tYes" in output
    assert "Platform:\t\t\tPlayStation 5" in output
    assert "PS+ user:\t\t\tTrue" in output
    assert "About me:\t\t\tHunting beasts" in output
    assert "Languages:\t\t\ten, pl" in output
    assert "Relation:\t\t\tfriend" in output
    assert "Mutual friends:\t\t\t7" in output
    assert "Profile URL:\t\t\thttps://psn.example/misiektoja" in output
    assert "User is currently in-game:\tBloodborne (PS4)" in output


# Verifies a user who is not a friend gets no mutual friend count, which PSN does not expose
def test_non_friends_show_no_mutual_friend_count(pm_module, info_user, capsys):
    info_user(presence=presence_payload(status="offline"), friendship={"friendRelation": "no relation"})

    pm_module.get_user_info(USER_ID, show_recent_games=False)

    output = capsys.readouterr().out
    assert "Relation:\t\t\tno relation" in output
    assert "Mutual friends" not in output


# Verifies a hidden mutual friend count is labeled rather than printed as a raw value
def test_hidden_mutual_friend_count_is_labeled(pm_module, info_user, capsys):
    info_user(presence=presence_payload(status="offline"), friendship={"friendRelation": "friend", "mutualFriendsCount": None})

    pm_module.get_user_info(USER_ID, show_recent_games=False)

    assert "Mutual friends:\t\t\tunknown" in capsys.readouterr().out


# Verifies an offline user is told when they were last seen and for how long they have been away
def test_offline_user_reports_when_they_were_last_seen(pm_module, info_user, capsys):
    info_user(presence=presence_payload(status="offline", last_online="2026-01-01T00:00:00Z"))

    pm_module.get_user_info(USER_ID, show_recent_games=False)

    output = capsys.readouterr().out
    assert "Last time user was available:\tThu 01 Jan 2026, 00:00:00" in output
    assert "User is OFFLINE for:" in output


# Verifies a recorded session start makes the report say how long the user has been online
def test_online_duration_uses_the_recorded_status(pm_module, info_user, isolated_working_directory, capsys):
    (isolated_working_directory / f"psn_{USER_ID}_last_status.json").write_text(json.dumps([1767225600, "online"]), encoding="utf-8")
    info_user(presence=presence_payload(status="online"))

    pm_module.get_user_info(USER_ID, show_recent_games=False)

    assert "User is ONLINE for:" in capsys.readouterr().out


# Verifies the recently played table lists each title with its platform, last played date and total time
def test_recently_played_games_are_tabulated(pm_module, info_user, capsys):
    user = info_user(presence=presence_payload(status="offline"), title_stats_value=[
        title_stat("Bloodborne", "ps4_game", datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc), timedelta(hours=23, minutes=47, seconds=54)),
        title_stat("Ratchet & Clank™: Rift Apart", "ps5_native_game", datetime(2025, 12, 24, 20, 30, tzinfo=timezone.utc), timedelta(days=1, hours=23, minutes=47, seconds=54)),
    ])

    pm_module.get_user_info(USER_ID, show_recent_games=True)

    output = capsys.readouterr().out
    assert user.title_stats_kwargs == {"limit": 10, "page_size": 50}
    assert "Bloodborne" in output
    assert "23:47:54" in output
    assert "1d 23:47:54" in output
    assert "Ratchet & Clank: Rift Apart" in output
    assert "ps4_game" in output


# Verifies a title that has never been launched shows no last played date instead of a broken cell
def test_never_played_title_shows_no_date(pm_module, info_user, capsys):
    info_user(presence=presence_payload(status="offline"), title_stats_value=[title_stat("Astro's Playroom", last_played=None, play_duration=None)])

    pm_module.get_user_info(USER_ID, show_recent_games=True)

    output = capsys.readouterr().out
    assert "n/a" in output
    assert "0:00:00" in output


# Verifies the recently played section is skipped entirely when it was not requested
def test_recently_played_section_can_be_skipped(pm_module, info_user, capsys):
    info_user(presence=presence_payload(status="offline"), title_stats_value=[title_stat("Bloodborne")])

    pm_module.get_user_info(USER_ID, show_recent_games=False)

    assert "recently played games" not in capsys.readouterr().out


# Verifies the trophy summary reports the level, the tier and the counts per trophy grade
def test_trophy_summary_is_reported(pm_module, info_user, capsys):
    earned = SimpleNamespace(platinum=3, gold=12, silver=40, bronze=180)
    info_user(presence=presence_payload(status="offline"), trophy_summary_value=SimpleNamespace(trophy_level=312, progress=45, tier=5, earned_trophies=earned))

    pm_module.get_user_info(USER_ID, include_trophies=True, show_recent_games=False)

    output = capsys.readouterr().out
    assert "Trophy level:\t\t\t312 (45% to next, tier 5)" in output
    assert "3 Platinum, 12 Gold, 40 Silver, 180 Bronze (235 total)" in output


# Verifies the most recent trophies are listed newest first with their title, grade and name
def test_last_earned_trophies_are_listed_newest_first(pm_module, info_user, capsys):
    titles = [SimpleNamespace(np_communication_id="NPWR12345_00", platform=SimpleNamespace(value="ps4"), trophy_title_name="Bloodborne")]
    trophies = [
        trophy("Vicar Amelia", "GOLD", earned_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)),
        trophy("Cleric Beast", "SILVER", earned_at=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)),
        trophy("Never earned", "BRONZE", earned=False, earned_at=datetime(2026, 1, 3, 10, 0, tzinfo=timezone.utc)),
    ]
    user = info_user(presence=presence_payload(status="offline"), titles=titles, trophies_by_title={"NPWR12345_00": trophies})

    pm_module.print_last_earned_trophies(user, max_items=5, title_limit=15)

    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith("- ")]
    assert lines == [
        "- Fri 02 Jan 2026, 10:00:00 | Bloodborne | SILVER | Cleric Beast",
        "- Thu 01 Jan 2026, 10:00:00 | Bloodborne | GOLD | Vicar Amelia",
    ]


# Verifies a hidden trophy is labeled instead of printed with an empty name
def test_hidden_trophies_are_labeled(pm_module, info_user, capsys):
    titles = [SimpleNamespace(np_communication_id="NPWR12345_00", platform=SimpleNamespace(value="ps5"), trophy_title_name="Elden Ring")]
    hidden = SimpleNamespace(trophy_name=None, trophy_type=SimpleNamespace(name="PLATINUM"), earned=True, earned_date_time=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc), hidden=True)
    user = info_user(presence=presence_payload(status="offline"), titles=titles, trophies_by_title={"NPWR12345_00": [hidden]})

    pm_module.print_last_earned_trophies(user)

    assert "| PLATINUM | (hidden)" in capsys.readouterr().out


# Verifies a restricted trophy list is explained rather than printed as an empty section
def test_restricted_trophy_visibility_is_explained(pm_module, info_user, capsys):
    user = info_user(presence=presence_payload(status="offline"))

    pm_module.print_last_earned_trophies(user)

    assert "no recent trophies found or trophy visibility is restricted" in capsys.readouterr().out


# Verifies a failing trophy lookup never stops the rest of the report from being printed
def test_failing_trophy_lookup_does_not_break_the_report(pm_module, info_user, capsys):
    info_user(presence=presence_payload(status="offline"), title_stats_value=[title_stat("Bloodborne")])

    pm_module.get_user_info(USER_ID, include_trophies=True, show_recent_games=True)

    output = capsys.readouterr().out
    assert "Trophy level" not in output
    assert "Bloodborne" in output


# Verifies a presence response the tool cannot read stops the report with a clear message
def test_unreadable_presence_stops_the_report(pm_module, info_user, capsys):
    broken = presence_payload(status="offline")
    broken["basicPresence"]["primaryPlatformInfo"] = None
    info_user(presence=broken)

    with pytest.raises(SystemExit) as raised:
        pm_module.get_user_info(USER_ID)

    assert raised.value.code == 1
    output = capsys.readouterr().out
    assert "unexpected shape" in output
    assert "To fix:" in output


# Verifies a rejected NPSSO stops the report instead of printing an empty profile
def test_rejected_npsso_stops_the_report(pm_module, monkeypatch, capsys):
    # Refuses to build a session the way an expired token does
    def refuse(npsso):
        raise RuntimeError("Your npsso code has expired")

    monkeypatch.setattr(pm_module, "PSNAWP", refuse)

    with pytest.raises(SystemExit) as raised:
        pm_module.get_user_info(USER_ID)

    assert raised.value.code == 1
    output = capsys.readouterr().out
    assert "did not accept the NPSSO code" in output
    assert "Generate a fresh NPSSO code" in output
