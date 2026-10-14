"""Smoke test #4b: SurrealDB Agent Memory remembers a typed fact and recalls it with a trace id.
usage: python scripts/check_memory.py   (needs SURREAL_MEMORY_URL, SURREAL_MEMORY_KEY, SURREAL_MEMORY_CONTEXT)"""
import json, sys, time
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from app import config
from app.memory import memory

assert memory.live, "set SURREAL_MEMORY_URL, SURREAL_MEMORY_KEY and SURREAL_MEMORY_CONTEXT"
memory.scope = "family/smoke-test"
fact = f"On {time.strftime('%Y-%m-%d')}, a smoke test forwarded a link to keystone-verifica.top. Guardian judged it a scam: the site asks for a password and is 3 days old."
print("remember ->", json.dumps(memory.remember(fact), ensure_ascii=False))
time.sleep(2)
res = memory.recall("Banco Keystone verifique su cuenta keystone-verifica.top")
print("recall   ->", "tier", res["tier"], "| trace", res["trace_id"], "|", len(res["hits"]), "hits")
for h in res["hits"]:
    print("   ", h["when"], h["score"], h["text"][:110])
prior = memory.prior_scam(res["hits"], {}, {"final_domain": "keystone-verifica.top"}, None, {"saved": False})
print("prior_scam ->", prior)
assert prior and prior["what"] == "link", "the remembered verdict did not come back"
print("OK: memory is live; retrieval traces visible in SurrealDB Studio -> Agent Memory -> context", config.SURREAL_MEMORY_CONTEXT[:8] + "...")
