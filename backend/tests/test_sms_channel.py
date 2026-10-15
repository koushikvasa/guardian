import os, sys
os.environ["GUARDIAN_MOCK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import config, sms


def test_whatsapp_prefix_added_and_stripped(monkeypatch):
    monkeypatch.setattr(config, "TWILIO_WHATSAPP_FROM", "+14155238886")
    assert sms._addr("+15714202558") == "whatsapp:+15714202558" and sms._addr("whatsapp:+1571") == "whatsapp:+1571" and sms.channel() == "whatsapp"
    monkeypatch.setattr(config, "TWILIO_WHATSAPP_FROM", "")
    assert sms._addr("whatsapp:+15714202558") == "+15714202558" and sms.channel() == "sms"
