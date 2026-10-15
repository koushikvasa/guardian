import os, sys, asyncio
os.environ["GUARDIAN_MOCK"] = "0"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import config


def test_dry_contextvar_turns_live_off_only_inside_its_task(monkeypatch):
    monkeypatch.setattr(config, "FORCE_MOCK", False)
    seen = {}

    async def dry_task():
        config.DRY.set(True)
        seen["inside"] = config.live("key")
        seen["thread"] = await asyncio.to_thread(config.live, "key")

    async def main():
        await asyncio.create_task(dry_task())
        seen["outside"] = config.live("key")
    asyncio.run(main())
    assert seen == {"inside": False, "thread": False, "outside": True}
