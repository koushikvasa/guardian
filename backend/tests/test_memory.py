import os, sys
os.environ["GUARDIAN_MOCK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import rules
from app.memory import Memory
from app.signals import regex_extract

DET = {"final_domain": "keystone-verifica.top", "brands": ["Keystone Bank"], "official_domain": False,
       "form_fields": ["Usuario", "Contraseña"], "domain_age_days": 3, "redirects": ["a", "b", "c"]}


def _case(text, det=DET):
    s = regex_extract(text)
    v = rules.evaluate(s, {"saved": False}, det, 0, "es")
    return {"id": "A-1", "text": text, "signals": s,
            "verdict": {"label": v.label, "fired": v.fired, "reasons": v.reasons()}}


def test_mock_memory_remembers_verdict_and_recalls_same_link():
    m = Memory()
    assert not m.live
    case = _case("Banco Keystone: Su cuenta está bloqueada. Verifique en 24 horas: bit.ly/kst-verif")
    m.remember_verdict(case, DET, None, "Rosa")
    res = m.recall_for_case({"id": "A-2", "text": "Keystone: verifique su cuenta hoy bit.ly/kst-verif", "signals": {}}, DET)
    assert res["hits"] and res["trace_id"]
    prior = Memory.prior_scam(res["hits"], {}, DET, None, {"saved": False})
    assert prior == {"what": "link", "date": res["hits"][0]["when"]}


def test_remembered_scam_rule_is_grounded_and_scores_scam():
    v = rules.evaluate({}, {"saved": False}, None, 0, "es", memory={"what": "link", "date": "2026-10-14"})
    assert v.label == "scam"
    f = next(x for x in v.fired if x["rule"] == "remembered_scam")
    assert "enlace" in f["reason"] and "link" in f["reason_en"] and f["reason"] in v.reasons()


def test_saved_family_number_never_matches_on_story():
    hits = [{"text": "On 2026-10-14, Rosa forwarded a text claiming to be daniel. Guardian judged it a scam: x", "when": "2026-10-14"}]
    assert Memory.prior_scam(hits, {"claimed_name": "Daniel"}, None, None, {"saved": True}) is None
    assert Memory.prior_scam(hits, {"claimed_name": "Daniel"}, None, None, {"saved": False}) == {"what": "story", "date": "2026-10-14"}


def test_seed_never_stores_phone_or_safe_phrase():
    m = Memory()
    m.seed_family({"name": "Familia Morales", "safe_phrase": "flan de la abuela", "second_key_threshold_usd": 500,
                   "members": [{"id": "rosa", "name": "Rosa", "role": "protected", "phone": "+1 555 010 0001", "lang": "es", "story_facts": ["Daniel lives in Queens"]},
                               {"id": "daniel", "name": "Daniel", "role": "guardian", "phone": "+1 555 010 0002", "lang": "en"}]})
    blob = " ".join(x["text"] for x in m.mem)
    assert "flan" not in blob and "0001" not in blob and "0002" not in blob
    assert "Daniel lives in Queens" in blob and m.scope == "family/familia-morales"
