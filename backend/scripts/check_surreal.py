"""Smoke test #4: load schema + seed family into SurrealDB, then read it back."""
import json, sys
sys.path.insert(0, ".")
from app.graph import graph
assert graph.live, "set SURREAL_URL (e.g. http://localhost:8001) — start with: surreal start --bind 0.0.0.0:8001 --user root --pass root memory"
graph.load_seed()
print(json.dumps(graph.family(), indent=2, ensure_ascii=False)[:1200])
graph.record_case({"id": "smoke-1", "text": "test"}, ["domain:keystone-verifica.top"])
print("herd hits for keystone-verifica.top:", graph.herd_hits(["domain:keystone-verifica.top"]))
