import os, sys, asyncio
os.environ["GUARDIAN_MOCK"] = "1"
os.environ["MOCK_CALL_SPEED"] = "0.01"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import pipeline
from app.graph import graph


def test_auto_forwarded_safe_text_is_silent_but_scam_still_speaks():
    graph.load_seed()
    safe = asyncio.run(pipeline.handle_message("+15550100005", "Dentist: your cleaning is Monday 10am.", "+12125550147", None, True))
    assert safe["verdict"]["label"] == "safe" and safe["outbound"] == []
    scam = asyncio.run(pipeline.handle_message("+15550100005", "Keystone Bank: account locked, verify now: bit.ly/kst-verif", "+12125550148", None, True))
    assert scam["verdict"]["label"] == "scam" and any("scam" in t.lower() for t in scam["outbound"])
