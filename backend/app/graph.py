"""SurrealDB: family trust graph + scam fingerprint graph.

Live mode talks to SurrealDB over its HTTP /sql endpoint (works with 1.x and 2.x).
Mock mode keeps the same shapes in memory, seeded from data/seed_family.json.
"""
import json
import re
from pathlib import Path

import httpx

from . import config

SEED = Path(__file__).resolve().parent.parent / "data" / "seed_family.json"
SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.surql"


def norm_phone(p: str) -> str:
    d = re.sub(r"\D", "", p or "")
    return "+" + (d if len(d) > 10 else "1" + d) if d else ""


def _key(p: str) -> str:
    return re.sub(r"\D", "", p)


class Graph:
    def __init__(self):
        self.live = config.live(config.SURREAL_URL)
        self.mem = {"people": {}, "family": None, "fingerprints": {}, "cases": {}}

    # ---------- low level ----------
    def sql(self, q: str, vars: dict | None = None):
        headers = {
            "Accept": "application/json",
            "surreal-ns": config.SURREAL_NS, "surreal-db": config.SURREAL_DB,  # 2.x
            "NS": config.SURREAL_NS, "DB": config.SURREAL_DB,  # 1.x
        }
        if vars:
            q = "".join(f"LET ${k} = {json.dumps(v, ensure_ascii=False)};\n" for k, v in vars.items()) + q
        r = httpx.post(config.SURREAL_URL.rstrip("/") + "/sql", content=q.encode(), headers=headers,
                       auth=(config.SURREAL_USER, config.SURREAL_PASS), timeout=10)
        r.raise_for_status()
        res = r.json()
        errs = [x for x in res if x.get("status") != "OK"]
        if errs:
            raise RuntimeError(errs)
        return res[-1]["result"]

    # ---------- setup ----------
    def load_seed(self, path: Path = SEED):
        fam = json.loads(path.read_text(encoding="utf-8"))
        if self.live:
            self.sql(SCHEMA.read_text(encoding="utf-8"))
            self.sql("DELETE person; DELETE family; DELETE member_of;")
            self.sql("CREATE family:main CONTENT $f;", {"f": {k: v for k, v in fam.items() if k != "members"}})
            for m in fam["members"]:
                m = {**m, "phone": norm_phone(m["phone"])}
                self.sql(f"CREATE person:{m['id']} CONTENT $m; RELATE person:{m['id']}->member_of->family:main SET role = $r;",
                         {"m": m, "r": m.get("role", "member")})
        else:
            self.mem["family"] = {k: v for k, v in fam.items() if k != "members"}
            for m in fam["members"]:
                self.mem["people"][m["id"]] = {**m, "phone": norm_phone(m["phone"])}
        return fam

    # ---------- family ----------
    def family(self) -> dict:
        if self.live:
            fam = (self.sql("SELECT * FROM family:main;") or [{}])[0]
            fam["members"] = self.sql("SELECT * FROM person;")
            return fam
        return {**(self.mem["family"] or {}), "members": list(self.mem["people"].values())}

    def person_by_phone(self, phone: str) -> dict | None:
        p = norm_phone(phone)
        for m in self.family()["members"]:
            if _key(m["phone"]) == _key(p):
                return m
        return None

    def person(self, pid: str) -> dict | None:
        return next((m for m in self.family()["members"] if str(m["id"]).split(":")[-1] == pid), None)

    def by_role(self, role: str) -> list[dict]:
        return [m for m in self.family()["members"] if m.get("role") == role]

    def sender_context(self, from_phone: str, protected_id: str) -> dict:
        p = self.person_by_phone(from_phone)
        return {"saved": p is not None, "trusted": p is not None and p.get("role") in ("guardian", "member", "protected"),
                "person": p, "protected_id": protected_id}

    def contacts_for_claim(self, claimed_name: str | None) -> list[dict]:
        """Who to call back: the claimed relative first (on their SAVED number), then guardians."""
        out = []
        if claimed_name:
            out += [m for m in self.family()["members"] if m.get("name", "").lower() == claimed_name.lower()]
        out += [m for m in self.by_role("guardian") if m not in out]
        return out

    # ---------- herd / fingerprints ----------
    def herd_hits(self, fingerprints: list[str]) -> int:
        fps = [f for f in fingerprints if f]
        if not fps:
            return 0
        if self.live:
            r = self.sql("SELECT count() AS n FROM fingerprint WHERE value IN $f GROUP ALL;", {"f": fps})
            return (r[0]["n"] if r else 0)
        return sum(self.mem["fingerprints"].get(f, 0) for f in fps)

    def record_case(self, case: dict, fingerprints: list[str]):
        if self.live:
            self.sql("CREATE type::thing('case', $id) CONTENT $c;", {"id": case["id"], "c": case})
            for f in fingerprints:
                if f:
                    self.sql("UPSERT type::thing('fingerprint', $f) SET value = $f, seen += 1; "
                             "RELATE (type::thing('case', $id))->has_fp->(type::thing('fingerprint', $f));",
                             {"f": f, "id": case["id"]})
        else:
            self.mem["cases"][case["id"]] = case
            for f in fingerprints:
                if f:
                    self.mem["fingerprints"][f] = self.mem["fingerprints"].get(f, 0) + 1


    # ---------- "same scam, reworded" (vector search) ----------
    def similar_scams(self, vec: list[float] | None, threshold: float = 0.85) -> list[dict]:
        if not (self.live and vec):
            return []
        try:
            rows = self.sql("SELECT id, text, vector::similarity::cosine(embedding, $v) AS sim "
                            "FROM scam_text WHERE embedding <|3,40|> $v;", {"v": vec})
            return [r for r in rows if r.get("sim", 0) >= threshold]
        except Exception:
            return []

    def store_scam_text(self, case_id: str, text: str, vec: list[float] | None):
        if self.live and vec:
            try:
                self.sql("CREATE type::thing('scam_text', $id) SET text = $t, embedding = $v;", {"id": case_id, "t": text, "v": vec})
            except Exception:
                pass


graph = Graph()
