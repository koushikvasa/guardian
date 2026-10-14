"""Smoke test #1 (riskiest): place ONE real outbound call to your own phone.
usage: python scripts/check_elevenlabs.py +1YOURNUMBER [es|en]"""
import sys, time, httpx
sys.path.insert(0, ".")
from app import config

to = sys.argv[1]; lang = sys.argv[2] if len(sys.argv) > 2 else "es"
agent = config.WARNING_AGENT_ID_ES if lang == "es" else config.WARNING_AGENT_ID_EN
assert config.ELEVENLABS_API_KEY and config.ELEVENLABS_PHONE_NUMBER_ID and agent, "set ELEVENLABS_API_KEY, ELEVENLABS_PHONE_NUMBER_ID, WARNING_AGENT_ID_*"
h = {"xi-api-key": config.ELEVENLABS_API_KEY}
r = httpx.post("https://api.elevenlabs.io/v1/convai/twilio/outbound-call", headers=h, timeout=20, json={
    "agent_id": agent, "agent_phone_number_id": config.ELEVENLABS_PHONE_NUMBER_ID, "to_number": to,
    "conversation_initiation_client_data": {"dynamic_variables": {"name": "Rosa", "safe_phrase": "flan de la abuela",
        "reasons": "La página pide su contraseña y fue creada hace 3 días.", "verdict": "estafa" if lang == "es" else "scam"}}})
print(r.status_code, r.text); r.raise_for_status()
cid = r.json()["conversation_id"]
for _ in range(60):
    time.sleep(3)
    c = httpx.get(f"https://api.elevenlabs.io/v1/convai/conversations/{cid}", headers=h).json()
    print(c.get("status"), len(c.get("transcript") or []), "lines")
    if c.get("status") in ("done", "failed"):
        print((c.get("analysis") or {}).get("data_collection_results")); break
