"""Shared pytest fixtures and import setup for the offline test suite.

These tests never touch the network. They import the single-file ``psn_monitor``
module and drive it with test doubles that stand in for the PlayStation Network.
"""

import os
import sys
from types import SimpleNamespace

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
elif sys.path.index(_PROJECT_ROOT) != 0:
    sys.path.remove(_PROJECT_ROOT)
    sys.path.insert(0, _PROJECT_ROOT)

import pytest

import psn_monitor as pm


# Fails fast when pytest imports an installed module instead of the working tree
def _assert_in_repo_module():
    resolved = os.path.abspath(pm.__file__)
    expected = os.path.join(_PROJECT_ROOT, "psn_monitor.py")
    assert resolved == expected, f"Tests imported the wrong psn_monitor module\n  imported: {resolved}\n  expected: {expected}"


_assert_in_repo_module()


# Raised by the test doubles to break out of the tool's endless monitoring loop
class LoopFinished(BaseException):
    pass


# Advances only when the code under test sleeps, so a monitoring run is deterministic and instant
class FakeClock:
    def __init__(self, start=1767222000):
        self.now = float(start)
        self.slept = []

    # Returns the current fake wall clock value
    def time(self):
        return self.now

    # Records a sleep and moves the fake clock forward by the same amount
    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += float(seconds)

    # Moves the fake clock forward without recording a sleep
    def advance(self, seconds):
        self.now += float(seconds)


# Builds a presence payload shaped like the one PSN returns
def presence_payload(status: "str | None" = "offline", platform_code: "str | None" = "PS5", game: "str | None" = None, launch_platform: "str | None" = None, last_online: "str | None" = None, availability: "str | None" = "availableToPlay"):
    game_title_info_list = []
    if game:
        game_title_info_list.append({"titleName": game, "launchPlatform": launch_platform})
    return {"basicPresence": {"availability": availability, "primaryPlatformInfo": {"onlineStatus": status, "platform": platform_code, "lastOnlineDate": last_online}, "gameTitleInfoList": game_title_info_list}}


# Stands in for a PSNAWP user and replays a scripted sequence of presence responses
class FakePsnUser:
    def __init__(self, script, account_id="1234567890", profile=None, friendship=None, share_link=None):
        self.script = list(script)
        self.account_id = account_id
        self.presence_calls = 0
        self._profile = profile if profile is not None else {"aboutMe": "Test profile", "isPlus": True, "languages": ["en"], "isOfficiallyVerified": False}
        self._friendship = friendship if friendship is not None else {"friendRelation": "friend", "mutualFriendsCount": 3}
        self._share_link = share_link if share_link is not None else {"shareUrl": "https://psn.example/misiektoja"}

    # Returns the next scripted presence payload, raising a scripted exception or ending the loop when the script runs out
    def get_presence(self):
        self.presence_calls += 1
        if not self.script:
            raise LoopFinished
        entry = self.script.pop(0)
        if isinstance(entry, BaseException):
            raise entry
        if callable(entry):
            return entry()
        return entry

    # Returns the canned profile document
    def profile(self):
        return self._profile

    # Returns the canned friendship document
    def friendship(self):
        return self._friendship

    # Returns the canned shareable profile link
    def get_shareable_profile_link(self):
        return self._share_link


# Stands in for the requests session inside a PSNAWP client and records whether the tool released it
class FakePsnHttpSession:
    def __init__(self):
        self.verify = True
        self.closed = False

    # Records that the tool closed the underlying HTTP session
    def close(self):
        self.closed = True


# Stands in for the PSNAWP client and records every session it is asked to build
class FakePSNAWP:
    instances: "list[FakePSNAWP]" = []
    psn_user: "FakePsnUser | None" = None

    def __init__(self, npsso):
        self.npsso = npsso
        self.closed = False
        # Mirrors the PSNAWP session the tool reaches for to apply the TLS verification setting
        self.authenticator = SimpleNamespace(request_builder=SimpleNamespace(session=FakePsnHttpSession()))
        FakePSNAWP.instances.append(self)

    # Returns the signed-in account, which is what the doctor reports after authenticating
    def me(self):
        return SimpleNamespace(online_id="signed-in-account")

    # Returns the fake user this class was primed with
    def user(self, online_id):
        self.online_id = online_id
        return FakePSNAWP.psn_user

    # Records that the tool closed the session
    def close(self):
        self.closed = True


# Exposes the imported module to every test
@pytest.fixture
def pm_module():
    return pm


# Resets the module globals the offline helpers read so every test starts from the same baseline
@pytest.fixture(autouse=True)
def deterministic_globals(monkeypatch):
    monkeypatch.setattr(pm, "LOCAL_TIMEZONE", "UTC", raising=False)
    monkeypatch.setattr(pm, "ASCII_LOG_SEPARATORS", "Auto", raising=False)
    monkeypatch.setattr(pm, "HORIZONTAL_LINE", 20, raising=False)
    monkeypatch.setattr(pm, "ACTIVE_INACTIVE_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(pm, "GAME_CHANGE_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(pm, "ERROR_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(pm, "VERIFY_SSL", True, raising=False)
    monkeypatch.setattr(pm, "WEBHOOK_ENABLED", False, raising=False)
    monkeypatch.setattr(pm, "WEBHOOK_PROVIDER", "discord", raising=False)
    monkeypatch.setattr(pm, "WEBHOOK_URL", "your_webhook_url", raising=False)
    monkeypatch.setattr(pm, "WEBHOOK_USERNAME", "PSN Monitor", raising=False)
    monkeypatch.setattr(pm, "WEBHOOK_AVATAR_URL", "", raising=False)
    monkeypatch.setattr(pm, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(pm, "WEBHOOK_GAME_CHANGE_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(pm, "WEBHOOK_ERROR_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(pm, "WEBHOOK_HEADERS", {}, raising=False)
    monkeypatch.setattr(pm, "WEBHOOK_TEMPLATE", dict(pm.WEBHOOK_TEMPLATE), raising=False)
    monkeypatch.setattr(pm, "WEBHOOK_TRANSFORMS", [], raising=False)
    monkeypatch.setattr(pm, "NTFY_ACCESS_TOKEN", "", raising=False)
    monkeypatch.setattr(pm, "PSN_CHECK_INTERVAL", 180, raising=False)
    monkeypatch.setattr(pm, "PSN_ACTIVE_CHECK_INTERVAL", 60, raising=False)
    monkeypatch.setattr(pm, "PSN_ACTIVE_CHECK_SIGNAL_VALUE", 30, raising=False)
    monkeypatch.setattr(pm, "OFFLINE_INTERRUPT", 420, raising=False)
    monkeypatch.setattr(pm, "LIVENESS_CHECK_INTERVAL", 43200, raising=False)
    monkeypatch.setattr(pm, "LIVENESS_CHECK_COUNTER", 240, raising=False)
    monkeypatch.setattr(pm, "LIVENESS_REMINDER_SECONDS", 43200, raising=False)
    monkeypatch.setattr(pm, "PSN_NPSSO", "npsso-test-value", raising=False)
    monkeypatch.setattr(pm, "SMTP_HOST", "smtp.example.test", raising=False)
    monkeypatch.setattr(pm, "SMTP_PORT", 587, raising=False)
    monkeypatch.setattr(pm, "SMTP_USER", "monitor@example.test", raising=False)
    monkeypatch.setattr(pm, "SMTP_PASSWORD", "not-a-real-password", raising=False)
    monkeypatch.setattr(pm, "SMTP_SSL", True, raising=False)
    monkeypatch.setattr(pm, "SENDER_EMAIL", "monitor@example.test", raising=False)
    monkeypatch.setattr(pm, "RECEIVER_EMAIL", "alerts@example.test", raising=False)
    monkeypatch.setattr(pm, "CSV_FILE", "", raising=False)
    monkeypatch.setattr(pm, "PSN_USER_ID", "", raising=False)
    monkeypatch.setattr(pm, "PSN_STATUS_FILE", "", raising=False)
    monkeypatch.setattr(pm, "DOTENV_FILE", "", raising=False)
    monkeypatch.setattr(pm, "DISABLE_LOGGING", True, raising=False)
    monkeypatch.setattr(pm, "CLEAR_SCREEN", False, raising=False)
    # Colour is resolved once at startup and left in module state, so without a reset a test that enables it
    # would colour the output every later test asserts on
    monkeypatch.setattr(pm, "COLORED_OUTPUT", False, raising=False)
    monkeypatch.setattr(pm, "COLOR_THEME", {}, raising=False)
    monkeypatch.setattr(pm, "COLOR_ENABLED", False, raising=False)
    monkeypatch.setattr(pm, "_COLOR_STYLES", {}, raising=False)
    # Startup assigns these directly rather than through a fixture, so without a reset a run with --debug or
    # --verbose would leave both modes on for every later test
    monkeypatch.setattr(pm, "VERBOSE_MODE", False, raising=False)
    monkeypatch.setattr(pm, "DEBUG_MODE", False, raising=False)
    # load_dotenv writes into os.environ and nothing removes it again, so a test that loads a dotenv would
    # otherwise leak its secrets into every later test through the exported-environment lookup at startup
    for secret in pm.SECRET_KEYS:
        monkeypatch.delenv(secret, raising=False)
    # Startup wraps sys.stdout in the sanitizing stream and a test that exits early never unwraps it, so the
    # wrappers would otherwise stack up across the session
    original_stdout = sys.stdout
    yield
    sys.stdout = original_stdout


# Collects every email the code under test tries to send instead of contacting an SMTP server
@pytest.fixture
def sent_emails(monkeypatch):
    delivered = []

    # Records one notification and reports success
    def fake_send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
        delivered.append({"subject": subject, "body": body, "body_html": body_html, "use_ssl": use_ssl})
        return 0

    monkeypatch.setattr(pm, "send_email", fake_send_email)
    return delivered


# Collects every webhook the code under test tries to send instead of contacting Discord or ntfy
@pytest.fixture
def sent_webhooks(monkeypatch):
    delivered = []

    # Records one alert and reports success
    def fake_send_webhook(title, description, notification_type="status", force=False, sleeper=None):
        delivered.append({"title": title, "description": description, "type": notification_type, "force": force})
        return 0

    monkeypatch.setattr(pm, "send_webhook", fake_send_webhook)
    return delivered


# Replaces wall clock reads and sleeps inside the module with a controllable fake clock
@pytest.fixture
def fake_clock(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(pm.time, "time", clock.time)
    monkeypatch.setattr(pm.time, "sleep", clock.sleep)
    return clock


# Neutralizes the alarm-based watchdog so the suite never installs a real SIGALRM handler
@pytest.fixture(autouse=True)
def no_alarm_signals(monkeypatch):
    monkeypatch.setattr(pm.signal, "alarm", lambda seconds: 0)
    monkeypatch.setattr(pm.signal, "signal", lambda sig, handler: None)
    yield


# Scripts the presence responses and exposes every session the tool built
class PsnSessionFactory:
    def __init__(self):
        FakePSNAWP.instances = []
        self.instances = FakePSNAWP.instances
        self.client_class = FakePSNAWP

    # Primes the double with a presence script and returns the fake user
    def __call__(self, script, **kwargs):
        user = FakePsnUser(script, **kwargs)
        FakePSNAWP.psn_user = user
        return user


# Installs the PSNAWP double and returns the factory that scripts the presence responses
@pytest.fixture
def psn_session(monkeypatch):
    monkeypatch.setattr(pm, "PSNAWP", FakePSNAWP)
    return PsnSessionFactory()
