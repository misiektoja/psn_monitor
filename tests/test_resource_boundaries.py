"""Exercise optional PSN lookups with real authentication and provider clients."""

import errno
import json

import psn_monitor as monitor


# Stops the real info flow when an optional trophy request exhausts file descriptors
def test_info_resource_exhaustion_stops_followup_requests(monkeypatch, capsys):
    from urllib.parse import urlparse
    import requests
    monkeypatch.setattr(monitor, "PSN_NPSSO", "synthetic-npsso")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    calls = []
    # Supplies realistic HTTP payloads to the real authentication and request handlers
    def send(session, request, **kwargs):
        endpoint = urlparse(request.url).path
        calls.append(endpoint)
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.status_code = 200
        payload = {}
        if "authorize" in endpoint:
            response.status_code = 302
            response.headers["location"] = "com.scee.psxandroid.scecompcall://redirect?code=synthetic-code"
        elif "oauth/token" in endpoint:
            payload = {"access_token": "synthetic-access", "refresh_token": "synthetic-refresh", "expires_in": 3600, "refresh_token_expires_in": 86400}
        elif "/profile2" in endpoint:
            payload = {"profile": {"accountId": "1234567890123456", "onlineId": "Example"}}
        elif "basicPresences" in endpoint:
            payload = {"basicPresence": {"primaryPlatformInfo": {"onlineStatus": "offline", "platform": "PS5", "lastOnlineDate": "2025-01-01T00:00:00Z"}}}
        elif "troph" in endpoint.lower():
            raise requests.ConnectionError("Connection failed") from OSError(errno.EMFILE, "Too many open files")
        elif "titles" in endpoint.lower():
            payload = {"titles": [], "totalItemCount": 0}
        elif "share" in endpoint.lower():
            payload = {"shareUrl": "https://profile.playstation.com/Example"}
        else:
            payload = {"aboutMe": "", "isPlus": False, "languages": ["en"], "friendRelation": "no"}
        response._content = json.dumps(payload).encode()
        return response
    monkeypatch.setattr(requests.Session, "send", send)
    assert monitor.get_user_info("Example", include_trophies=True, show_recent_games=True) is False
    assert calls[-1].endswith("/trophySummary")
    assert len(calls) == 8
    assert "file descriptors" in capsys.readouterr().out.lower()
