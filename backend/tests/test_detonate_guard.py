import os, sys, asyncio
os.environ["GUARDIAN_MOCK"] = "0"
os.environ["ANCHOR_API_KEY"] = "sk-bogus"
os.environ["DAYTONA_API_KEY"] = ""
os.environ["DETONATE_MODE"] = "local"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import detonate, bus


def test_anchor_failure_does_not_crash_the_case(monkeypatch):
    async def boom():
        raise RuntimeError("402 Payment Required")
    monkeypatch.setattr(detonate, "_anchor_session", boom)
    res = asyncio.run(detonate.detonate("https://example.com", "T-1"))
    assert res["mode"] == "local" and "402" in res["error"] and res["final_domain"] is None
    assert any(e["kind"] == "detonation.error" and e["case"] == "T-1" for e in bus.history)
