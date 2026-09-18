"""Exercise PSNAWP's real lazy iterators and private authentication errors."""

import json
import signal

import pytest
from psnawp_api import PSNAWP
from requests.adapters import HTTPAdapter

import psn_monitor as monitor
from psn_http_peer import EndScenario, PsnHTTPPeer


# Runs the complete report using actual PSNAWP objects and realistic HTTP responses
def test_ps4_trophies_and_pipe_titles_survive_the_real_report(tmp_path, monkeypatch, capsys):
    peer = PsnHTTPPeer("info")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "PSNAWP", PSNAWP)
    monkeypatch.setattr(monitor, "PSN_NPSSO", "a" * 64)
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(HTTPAdapter, "send", lambda adapter, request, **kwargs: peer.send(adapter, request, **kwargs))
    assert monitor.get_user_info("ReviewUser", include_trophies=True) is not False
    output = capsys.readouterr().out
    assert "Earned PS4 Trophy" in output
    assert "Alpha | Beta" in output
    assert not any(item["query"].get("npServiceName") == ["trophy2"] for item in peer.requests)


# Redacts a provider response that repeats a candidate not yet saved in configuration
def test_private_npsso_rejection_redacts_the_entered_candidate(tmp_path, monkeypatch, capsys):
    import requests

    candidate = "synthetic-candidate-" + "q" * 46

    # Returns the attempted credential in a realistic provider rejection
    def reject(adapter, request, **kwargs):
        assert request.headers["Cookie"] == "npsso=" + candidate
        response = requests.Response()
        response.status_code = 401
        response.url = request.url
        response.request = request
        response._content = ("Rejected credential " + candidate).encode()
        return response

    monkeypatch.setattr(monitor, "PSNAWP", PSNAWP)
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monkeypatch.setattr(HTTPAdapter, "send", reject)
    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_npsso(env_file=str(tmp_path / ".env"), interactive=True, getpass_func=lambda _: candidate)
    monitor.print_recovery_advice(raised.value.advice)
    output = capsys.readouterr().out
    assert candidate not in output
    assert "<redacted>" in output
    assert not (tmp_path / ".env").exists()


# Keeps remote authentication details out of an ordinary monitoring transcript
def test_monitoring_auth_failure_uses_quiet_recovery(tmp_path, monkeypatch, capsys):
    peer = PsnHTTPPeer("quiet-auth-error")
    monkeypatch.chdir(tmp_path)
    for name, value in {"PSNAWP": PSNAWP, "PSN_NPSSO": "a" * 64, "LOCAL_TIMEZONE": "UTC", "DEBUG_MODE": False, "PSN_CHECK_INTERVAL": 0.001, "PSN_ACTIVE_CHECK_INTERVAL": 0.001, "ERROR_NOTIFICATION": False}.items():
        monkeypatch.setattr(monitor, name, value)
    monkeypatch.setattr(HTTPAdapter, "send", lambda adapter, request, **kwargs: peer.send(adapter, request, **kwargs))
    try:
        with pytest.raises(EndScenario):
            monitor.psn_monitor_user("ReviewUser", "")
    finally:
        if hasattr(signal, "alarm"):
            signal.alarm(0)
    output = capsys.readouterr().out
    assert "rejected the NPSSO" in output
    assert "Technical detail:" not in output


# Preserves future-dated history and explains recovery instead of computing an impossible age
def test_future_status_keeps_monitoring_and_restarts_its_timing(tmp_path, monkeypatch, capsys):
    path = tmp_path / "psn_ReviewUser_last_status.json"
    record = [253402214400, "offline", {"owner_note": "keep"}]
    path.write_text(json.dumps(record))
    peer = PsnHTTPPeer("state-future")
    monkeypatch.chdir(tmp_path)
    for name, value in {"PSNAWP": PSNAWP, "PSN_NPSSO": "a" * 64, "LOCAL_TIMEZONE": "UTC", "PSN_CHECK_INTERVAL": 0.001, "PSN_ACTIVE_CHECK_INTERVAL": 0.001, "ERROR_NOTIFICATION": False}.items():
        monkeypatch.setattr(monitor, name, value)
    monkeypatch.setattr(HTTPAdapter, "send", lambda adapter, request, **kwargs: peer.send(adapter, request, **kwargs))
    try:
        # Monitoring continues past the saved history and stops only where the scenario runs out of responses
        with pytest.raises(EndScenario):
            monitor.psn_monitor_user("ReviewUser", "")
    finally:
        if hasattr(signal, "alarm"):
            signal.alarm(0)
    output = capsys.readouterr().out
    assert "dated ahead of this machine's clock" in output
    assert "Keeping the saved status OFFLINE" in output
    assert "7973" not in output
