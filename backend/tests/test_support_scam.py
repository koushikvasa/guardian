import os, sys
os.environ["GUARDIAN_MOCK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import rules
from app.signals import regex_extract


def _v(text, lang="en"):
    s = regex_extract(text)
    return s, rules.evaluate(s, {"saved": False, "trusted": False}, None, 0, lang)


def test_microsoft_call_with_anydesk_and_gift_cards_is_a_critical_scam():
    s, v = _v("A man from Microsoft just called, says my computer has a virus. He wants me to install AnyDesk and buy $500 Google Play cards to fix it. Call back 1-888-555-0199")
    assert s["remote_access"] and s["tech_support_claim"] and s["brand"] == "Microsoft" and s["callback_number"].endswith("0199")
    assert s["money_request"] == {"amount": 500.0, "method": "gift_card"}
    fired = {f["rule"] for f in v.fired}
    assert {"remote_access_request", "unsolicited_tech_support", "callback_number_bait", "untraceable_payment"} <= fired
    assert v.label == "scam" and v.critical


def test_telugu_and_spanish_support_stories_are_caught():
    _, te = _v("Microsoft నుంచి అని ఒకాయన కాల్ చేశాడు, నా కంప్యూటర్‌లో వైరస్ ఉందంట. AnyDesk ఇన్‌స్టాల్ చేయమని అంటున్నాడు", "te")
    _, es = _v("Me llamó alguien de soporte técnico de Microsoft, dice que mi computadora tiene un virus y quiere acceso remoto", "es")
    assert te.label == "scam" and es.label == "scam"
    assert all("Microsoft" in f["reason"] for f in te.fired if f["rule"] == "unsolicited_tech_support")


def test_brand_alone_is_not_a_scam():
    _, v = _v("Reminder: your Microsoft Teams meeting with the school starts at 3pm today")
    assert v.label == "safe" and not v.fired
