import os, sys, asyncio
os.environ["GUARDIAN_MOCK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import bus, config, detonate


def test_anchor_failure_does_not_crash_the_case(monkeypatch):
    # config is read at import time, so patch its attributes rather than the environment
    monkeypatch.setattr(config, "FORCE_MOCK", False)
    monkeypatch.setattr(config, "ANCHOR_API_KEY", "sk-bogus")
    monkeypatch.setattr(config, "DAYTONA_API_KEY", "")
    monkeypatch.setattr(config, "DETONATE_MODE", "local")

    async def boom():
        raise RuntimeError("402 Payment Required")
    monkeypatch.setattr(detonate, "_anchor_session", boom)
    res = asyncio.run(detonate.detonate("https://example.com", "T-1"))
    assert res["mode"] == "local" and "402" in res["error"] and res["final_domain"] is None
    assert any(e["kind"] == "detonation.error" and e["case"] == "T-1" for e in bus.history)
