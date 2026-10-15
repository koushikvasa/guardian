import os, sys, asyncio
os.environ["GUARDIAN_MOCK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import config, main, pipeline


def test_fragments_from_one_sender_become_one_case(monkeypatch):
    monkeypatch.setattr(config, "INGEST_MERGE_S", 0.2)
    calls = []

    async def fake(phone, body, sender, pid, quiet):
        calls.append((phone, body, sender, quiet))
    monkeypatch.setattr(pipeline, "handle_message", fake)

    async def run():
        await main.queue_ingest("+15550100005", "+15513287169", "Keystone Bank: Your account is locked. Verify within 24 hours:")
        await asyncio.sleep(0.05)
        await main.queue_ingest("+15550100005", "+15513287169", "https://example.test/mock/keystone/")
        await main.queue_ingest("+15550100005", "+12125550147", "Dentist Monday 10am")
        await asyncio.sleep(0.5)
    asyncio.run(run())
    assert len(calls) == 2
    joined = next(c for c in calls if c[2] == "+15513287169")
    assert joined[1] == "Keystone Bank: Your account is locked. Verify within 24 hours: https://example.test/mock/keystone/" and joined[3] is True


def test_bank_account_locked_is_not_tech_support():
    from app.signals import regex_extract
    assert not regex_extract("Keystone Bank: Your account is locked. Verify within 24 hours:")["tech_support_claim"]
