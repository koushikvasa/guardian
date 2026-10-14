"""SurrealDB Agent Memory: what Guardian remembers across cases and restarts.

Live: the hosted Agent Memory API. Every fact is typed on write (entities, attributes, relations)
      and every recall returns a retrieval trace id, so Daniel's screen can show *why* Guardian knows it.
Mock: the same shapes in memory (keyword overlap), so every screen behaves identically without a key.

Only scrubbed text goes in. Phone numbers are reduced to their last 4 digits. The family safe phrase never goes in.
The verdict stays deterministic: a recalled memory only counts when it names the same domain, sender or claim.
"""
import re
import time
from pathlib import Path

import httpx

from . import bus, config
from .tracing import span

VERDICT_TAG = "Guardian judged it a scam"
_SEEDED = Path(__file__).resolve().parent.parent / "data" / ".memory_seeded"


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-záéíóúñü0-9]{4,}", s.lower())}


def _last4(phone: str | None) -> str:
    return re.sub(r"\D", "", phone or "")[-4:]


class Memory:
    def __init__(self):
        self.live = config.live(config.SURREAL_MEMORY_URL, config.SURREAL_MEMORY_KEY, config.SURREAL_MEMORY_CONTEXT)
        self.scope = "family/main"
        self.mem: list[dict] = []  # mock twin: [{text, at}]
        self._scopes_ok: set[str] = set()

    # ---------- transport ----------
    def _base(self) -> str:
        return config.SURREAL_MEMORY_URL.strip().rstrip("/") + "/api/v1/" + config.SURREAL_MEMORY_CONTEXT.strip()

    def _h(self) -> dict:
        return {"Authorization": f"Bearer {config.SURREAL_MEMORY_KEY}", "Content-Type": "application/json"}

    def _ensure_scope(self, scope: str):
        if scope in self._scopes_ok or not self.live:
            return
        try:  # 201 created or 409 exists; either is fine
            httpx.post(self._base() + "/scopes", headers=self._h(), json={"path": scope}, timeout=15)
        except Exception:
            pass
        self._scopes_ok.add(scope)

    # ---------- remember ----------
    def remember(self, text: str, case_id: str | None = None) -> dict:
        with span("memory.remember", case=case_id or "") as s:
            entities, attributes = [], 0
            if self.live:
                try:
                    self._ensure_scope(self.scope)
                    r = httpx.post(self._base() + "/facts", headers=self._h(), timeout=60,
                                   json={"text": text, "infer": "full", "scopes": [self.scope]})
                    r.raise_for_status()
                    ex = r.json().get("extraction") or {}
                    entities = [e.get("name") for e in ex.get("entities", []) if e.get("name")]
                    attributes = len(ex.get("attributes") or [])
                except Exception as e:
                    bus.emit("memory.error", case_id, op="remember", error=str(e)[:200])
                    return {"ok": False}
            else:
                self.mem.append({"text": text, "at": time.time()})
                entities = [w for w in re.findall(r"\b[A-Z][a-z]{2,}\b", text) if w not in ("On", "Guardian", "The")][:6]
            s.set("entities", ", ".join(entities))
            bus.emit("memory.remembered", case_id, text=text, entities=entities, attributes=attributes)
            return {"ok": True, "entities": entities}

    # ---------- recall ----------
    def recall(self, query: str, case_id: str | None = None, limit: int = 5) -> dict:
        """Returns {hits: [{text, when, score}], trace_id, tier}. Never raises."""
        with span("memory.recall", case=case_id or "") as s:
            out: dict = {"hits": [], "trace_id": None, "tier": None}
            if self.live:
                try:
                    r = httpx.post(self._base() + "/query", headers=self._h(), timeout=25,
                                   json={"query": query[:600], "lens": [self.scope]})
                    r.raise_for_status()
                    d = r.json()
                    out["tier"] = d.get("tier")
                    out["trace_id"] = (d.get("trace") or {}).get("traceId")
                    for h in d.get("hits") or []:
                        if h.get("source") == "memory_chunk" and h.get("text"):
                            out["hits"].append({"text": h["text"], "when": (h.get("occurredAt") or "")[:10],
                                                "score": round(float(h.get("score") or 0), 2)})
                except Exception as e:
                    bus.emit("memory.error", case_id, op="recall", error=str(e)[:200])
            else:
                qt = _tokens(query)
                scored = []
                for m in self.mem:
                    ov = len(qt & _tokens(m["text"]))
                    if ov >= 2:
                        scored.append((ov / max(1, len(qt)), m))
                scored.sort(key=lambda x: -x[0])
                out["hits"] = [{"text": m["text"], "when": time.strftime("%Y-%m-%d", time.localtime(m["at"])), "score": round(sc, 2)}
                               for sc, m in scored]
                out["tier"], out["trace_id"] = "mock", "mock"
            out["hits"] = out["hits"][:limit]
            s.set("hits", len(out["hits"]))
            s.set("trace_id", out["trace_id"] or "")
            return out

    # ---------- what a case does with memory ----------
    def recall_for_case(self, case: dict, det: dict | None) -> dict:
        s = case.get("signals") or {}
        q = " ".join(x for x in [case["text"], (det or {}).get("final_domain") or "", s.get("claimed_name") or ""] if x)
        return self.recall(q, case["id"])

    @staticmethod
    def prior_scam(hits: list[dict], signals: dict, det: dict | None, sender_phone: str | None, sender: dict) -> dict | None:
        """Deterministic match against remembered verdicts: same final domain, same sender, or same family claim."""
        dom = ((det or {}).get("final_domain") or "").lower()
        last4 = _last4(sender_phone)
        claimed = (signals.get("claimed_name") or "").lower()
        for h in hits:
            tl = h["text"].lower()
            if VERDICT_TAG.lower() not in tl:
                continue
            if dom and dom in tl:
                return {"what": "link", "date": h["when"]}
            if sender.get("saved"):
                continue  # a saved family number never matches on story or sender
            if last4 and f"ending {last4}" in tl:
                return {"what": "sender", "date": h["when"]}
            if claimed and f"claiming to be {claimed}" in tl:
                return {"what": "story", "date": h["when"]}
        return None

    def remember_verdict(self, case: dict, det: dict | None, sender_phone: str | None, protected_name: str):
        if case["verdict"]["label"] != "scam":
            return
        s = case.get("signals") or {}
        bits = []
        dom = (det or {}).get("final_domain")
        if dom:
            bits.append(f"a link to {dom}")
        if s.get("claims_family"):
            bits.append(f"a text claiming to be {s.get('claimed_name') or 'a relative'}")
        m = s.get("money_request") or {}
        if m.get("method"):
            bits.append(f"asking for money by {m['method']}")
        if _last4(sender_phone):
            bits.append(f"from a number ending {_last4(sender_phone)}")
        what = ", ".join(bits) or "a suspicious message"
        reasons = [f.get("reason_en") or f["reason"] for f in case["verdict"]["fired"]
                   if f["weight"] > 0 and f["rule"] not in ("herd_match", "remembered_scam")][:3]  # first-hand evidence only
        text = f"On {time.strftime('%Y-%m-%d')}, {protected_name} forwarded {what}. {VERDICT_TAG}: " + " ".join(reasons)
        self.remember(text, case["id"])

    def seed_family(self, fam: dict):
        """Trust facts, once per memory context. No phone numbers, no safe phrase."""
        name = fam.get("name") or "the family"
        self.scope = "family/" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        marker = _SEEDED.with_suffix("." + (config.SURREAL_MEMORY_CONTEXT or "mock")[:12])
        if self.live and marker.exists():
            return
        members = fam.get("members") or []
        protected = next((m for m in members if m.get("role") == "protected"), None)
        facts = []
        for m in members:
            role = {"protected": "the protected member", "guardian": "the family guardian", "member": "a family member"}.get(m.get("role"), "a member")
            facts.append(f"{m['name']} is {role} of {name} and speaks {'Spanish' if m.get('lang') == 'es' else 'English'}.")
        for fact in (protected or {}).get("story_facts") or []:
            facts.append(f"{protected['name']} knows this about her family: {fact}.")
        if fam.get("second_key_threshold_usd"):
            g = next((m["name"] for m in members if m.get("role") == "guardian"), "a guardian")
            facts.append(f"In {name}, any money request above ${fam['second_key_threshold_usd']} must wait for {g}'s second key.")
        for f in facts:
            self.remember(f)
        try:
            marker.parent.mkdir(exist_ok=True)
            marker.write_text(time.strftime("%Y-%m-%d %H:%M"), encoding="utf-8")
        except Exception:
            pass


memory = Memory()
