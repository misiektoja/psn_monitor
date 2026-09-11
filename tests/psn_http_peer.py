import json
from urllib.parse import parse_qs, urlsplit
import requests


# Stops a bounded run at the HTTP boundary after the relevant output was produced
class EndScenario(BaseException):
    pass


# Supplies PSN responses without replacing clients or iterators
class PsnHTTPPeer:
    # Starts a response script for one scenario
    def __init__(self, scenario):
        self.scenario = scenario
        self.requests = []
        self.presences = 0
        self.authorizations = 0

    # Returns a real requests response for one prepared request
    def send(self, adapter, request, **kwargs):
        url = urlsplit(request.url)
        query = parse_qs(url.query)
        path = url.path
        self.requests.append({"method": request.method, "path": path, "query": query, "verify": kwargs.get("verify")})
        status, payload, headers = 200, {}, {}
        if path.endswith("/oauth/authorize"):
            self.authorizations += 1
            if self.scenario == "quiet-auth-error" and self.presences > 1:
                if self.authorizations > 2:
                    raise EndScenario()
                headers["location"] = "com.scee.psxandroid.scecompcall://redirect?error=access_denied&error_code=4165&error_description=synthetic-provider-detail"
            else:
                headers["location"] = "com.scee.psxandroid.scecompcall://redirect?code=synthetic-authorization"
            status = 302
        elif path.endswith("/oauth/token"):
            payload = {"access_token": "synthetic-access", "refresh_token": "synthetic-refresh", "expires_in": 3600, "refresh_token_expires_in": 3600}
        elif path.endswith("/profile2"):
            payload = {"profile": {"onlineId": "ReviewUser", "accountId": "1234567890123456789"}}
        elif path.endswith("/profiles"):
            payload = {"onlineId": "ReviewUser", "aboutMe": "Synthetic profile", "isPlus": True, "languages": ["en"], "isOfficiallyVerified": False}
        elif path.endswith("/summary") and "/friends/" in path:
            payload = {"friendRelation": "friend", "mutualFriendsCount": 0}
        elif "/share/profile/" in path:
            payload = {"shareUrl": "https://profile.playstation.com/ReviewUser"}
        elif path.endswith("/basicPresences"):
            self.presences += 1
            if self.scenario == "quiet-auth-error" and self.presences > 1:
                status, payload = 401, {"error": {"message": "Synthetic private API detail"}}
            elif self.scenario.startswith("state-") and self.presences > 1:
                raise EndScenario()
            else:
                payload = {"basicPresence": {"primaryPlatformInfo": {"onlineStatus": "offline", "platform": "PS5", "lastOnlineDate": "2026-09-13T10:00:00Z"}, "availability": "notAvailable", "gameTitleInfoList": []}}
        elif path.endswith("/trophySummary"):
            payload = {"trophyLevel": 10, "progress": 20, "tier": 1, "earnedTrophies": {"bronze": 1, "silver": 0, "gold": 0, "platinum": 0}}
        elif path.endswith("/trophyTitles"):
            payload = {"totalItemCount": 1, "trophyTitles": [{"npCommunicationId": "NPWR00001_00", "npServiceName": "trophy", "trophyTitleName": "Synthetic PS4 Game", "trophyTitlePlatform": "PS4", "lastUpdatedDateTime": "2026-09-13T10:00:00Z"}]}
        elif path.endswith("/trophies"):
            if query.get("npServiceName") == ["trophy2"]:
                status, payload = 404, {"error": {"code": 2113426, "message": "Resource not found for trophy2"}}
            else:
                payload = {"totalItemCount": 1, "trophies": [{"trophyId": 0, "trophyType": "bronze", "trophyName": "Earned PS4 Trophy", "trophyHidden": False, "earned": True, "earnedDateTime": "2026-09-13T10:00:00Z", "trophyEarnedRate": "10.0"}]}
        elif path.endswith("/titles"):
            payload = {"totalItemCount": 1, "titles": [{"titleId": "CUSA00001_00", "name": "Alpha | Beta", "category": "ps4_game", "playCount": 3, "firstPlayedDateTime": "2026-09-01T10:00:00Z", "lastPlayedDateTime": "2026-09-13T10:00:00Z", "playDuration": "PT1H2M3S"}]}
        elif path not in ("/", "/api"):
            raise AssertionError("Unexpected request: " + request.method + " " + request.url)
        response = requests.Response()
        response.status_code = status
        response.url = request.url
        response.request = request
        response.headers.update(headers)
        response._content = json.dumps(payload).encode()
        return response
