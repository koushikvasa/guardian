import os, sys, asyncio
os.environ["GUARDIAN_MOCK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import bus, config, sms


def _last():
    return [e for e in bus.history if e["kind"] == "sms.out"][-1]


def _live(monkeypatch):
    monkeypatch.setattr(config, "FORCE_MOCK", False)
    monkeypatch.setattr(config, "TWILIO_ACCOUNT_SID", "AC")
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "x")
    monkeypatch.setattr(config, "TWILIO_WHATSAPP_FROM", "+1")


def test_essential_only_skips_ack(monkeypatch):
    _live(monkeypatch)
    monkeypatch.setattr(config, "TEXT_ESSENTIAL_ONLY", True)
    monkeypatch.setattr(config, "TEXT_BUDGET", 0)
    asyncio.run(sms.send("T", "+15550100005", "ack", key="ack"))
    assert _last()["skipped"] == "not essential" and _last()["delivered"] is False


def test_budget_exhausted_skips_without_error(monkeypatch, tmp_path):
    _live(monkeypatch)
    monkeypatch.setattr(config, "TEXT_ESSENTIAL_ONLY", False)
    monkeypatch.setattr(config, "TEXT_BUDGET", 1)
    monkeypatch.setattr(sms, "_COUNTER", tmp_path / "c.json")
    (tmp_path / "c.json").write_text('{"sent": 1}')
    asyncio.run(sms.send("T", "+15550100005", "hello", key="scam_calling"))
    assert _last()["skipped"] == "budget exhausted"
