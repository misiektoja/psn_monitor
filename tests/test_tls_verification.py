"""Tests for VERIFY_SSL: which requests honour it, what is reported while it is off and its shipped default."""

import ssl
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "psn_monitor.py").read_text(encoding="utf-8")
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"


# Records the keyword arguments of every request made through it and answers with an empty success
class RecordingRequests:
    def __init__(self):
        self.calls = []

    # Stands in for both requests.get and Session.post, which the tool calls with keyword arguments only
    def __call__(self, url=None, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return SimpleNamespace(status_code=204, headers={}, text="", reason="No Content")

    # Returns the TLS setting the single recorded request carried
    def verified(self):
        assert len(self.calls) == 1, f"expected one request, recorded {len(self.calls)}"
        return self.calls[0].get("verify")


@pytest.fixture
# Returns a recorder installed over every outbound request the tool can make
def outbound(pm_module, monkeypatch):
    recorder = RecordingRequests()
    monkeypatch.setattr(pm_module.req, "get", recorder)
    monkeypatch.setattr(pm_module, "WEBHOOK_SESSION", SimpleNamespace(post=recorder))
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", WEBHOOK_URL)
    return recorder


@pytest.mark.parametrize("verify", [True, False])
# Verifies the connectivity check carries the configured setting rather than the requests library default
def test_the_connectivity_check_honours_the_setting(pm_module, monkeypatch, outbound, verify):
    monkeypatch.setattr(pm_module, "VERIFY_SSL", verify)

    assert pm_module.check_internet("https://psn.example/probe", 5) is True
    assert outbound.verified() is verify


@pytest.mark.parametrize("verify", [True, False])
# Verifies the auth probe carries the setting, since it reaches PSN outside the PSNAWP session
def test_the_auth_probe_honours_the_setting(pm_module, monkeypatch, outbound, verify):
    monkeypatch.setattr(pm_module, "VERIFY_SSL", verify)

    assert pm_module.probe_npsso_auth_error("a-code") is None
    assert outbound.verified() is verify


@pytest.mark.parametrize("verify", [True, False])
# Verifies webhook deliveries carry the setting, so one channel cannot skip a check the others make
def test_the_webhook_delivery_honours_the_setting(pm_module, monkeypatch, outbound, verify):
    monkeypatch.setattr(pm_module, "VERIFY_SSL", verify)

    pm_module.post_webhook_request(json={"content": "hello"})

    assert outbound.verified() is verify


@pytest.mark.parametrize("verify", [True, False])
# Verifies the PSN session is configured before it signs in, which is where the NPSSO is exchanged for a token
def test_the_psn_session_honours_the_setting(pm_module, monkeypatch, psn_session, verify):
    monkeypatch.setattr(pm_module, "VERIFY_SSL", verify)

    client = pm_module.psn_client("a-code")

    assert client.authenticator.request_builder.session.verify is verify


# Refuses a client that cannot honor the configured certificate policy
def test_a_psn_client_without_tls_control_is_refused(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "VERIFY_SSL", False)
    monkeypatch.setattr(pm_module, "PSNAWP", lambda npsso: SimpleNamespace(npsso=npsso))

    with pytest.raises(pm_module.RecoveryError, match="cannot apply VERIFY_SSL"):
        pm_module.psn_client("a-code")


@pytest.mark.parametrize("verify", [True, False])
# Verifies the SMTP handshake follows the setting, so email is not the one channel that keeps checking certificates
def test_the_smtp_context_honours_the_setting(pm_module, monkeypatch, verify):
    monkeypatch.setattr(pm_module, "VERIFY_SSL", verify)

    context = pm_module.smtp_ssl_context()

    assert context.check_hostname is verify
    assert (context.verify_mode == ssl.CERT_REQUIRED) is verify


# Verifies no SMTP call site builds its own context, which would keep that one connection verifying while the setting is off
def test_only_the_shared_helper_builds_an_smtp_context():
    assert SOURCE.count("ssl.create_default_context()") == 1


@pytest.mark.parametrize("verify, silenced", [(True, False), (False, True)])
# Verifies the certificate warning is silenced only once the reader has chosen to switch verification off
def test_the_certificate_warning_is_silenced_only_while_verification_is_off(pm_module, monkeypatch, verify, silenced):
    disabled = []
    monkeypatch.setattr(pm_module, "VERIFY_SSL", verify)
    monkeypatch.setattr(pm_module.urllib3, "disable_warnings", lambda category: disabled.append(category))

    pm_module.apply_tls_verification_setting()

    assert bool(disabled) is silenced


# Verifies the doctor passes the setting silently while it is on
def test_the_doctor_passes_while_verification_is_on(pm_module):
    check = next(item for item in pm_module.doctor_check_configuration() if "TLS" in item.label)

    assert (check.status, check.advice) == ("PASS", None)


# Verifies the doctor warns while verification is off and names the setting to change and where it is documented
def test_the_doctor_warns_while_verification_is_off(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "VERIFY_SSL", False)

    check = next(item for item in pm_module.doctor_check_configuration() if "TLS" in item.label)

    assert check.status == "WARN"
    assert "VERIFY_SSL" in check.detail
    assert "VERIFY_SSL" in check.advice.fix
    assert pm_module.TLS_GUIDE_URL in check.advice.fix


@pytest.mark.parametrize("verify, concise", [(True, False), (False, True)])
# Verifies the summary always records the setting and puts it in front of the reader only when it is off
def test_the_summary_promotes_the_row_only_while_verification_is_off(pm_module, monkeypatch, verify, concise):
    monkeypatch.setattr(pm_module, "VERIFY_SSL", verify)

    row = next(item for item in pm_module.build_startup_summary("misiektoja", None, None, None) if item.label == "TLS verification")

    assert (row.full, row.concise) == (True, concise)
    assert row.value.startswith("On" if verify else "Off")


# Verifies certificates are verified unless the reader turns that off, in the shipped config and the fallback alike
def test_certificates_are_verified_by_default(pm_module):
    shipped = pm_module.parse_config_content(pm_module.CONFIG_BLOCK, "<built-in-config>")

    assert shipped["VERIFY_SSL"] is True
    assert pm_module.VERIFY_SSL is True
