import os, sys
os.environ["GUARDIAN_MOCK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import rules
from app.signals import regex_extract
from app.scrub import scrub
from app.live_evals import asks_for_secrets
import re

DET = {"final_domain": "keystone-verifica.top", "brands": ["Keystone Bank"], "official_domain": False,
       "form_fields": ["Usuario", "Contraseña"], "domain_age_days": 3, "redirects": ["a", "b", "c"]}


def test_keystone_link_is_scam_with_cited_reasons():
    s = regex_extract("Banco Keystone: Su cuenta está bloqueada. Verifique en 24 horas: bit.ly/kst-verif")
    v = rules.evaluate(s, {"saved": False}, DET, 0, "es")
    assert v.label == "scam" and v.score >= 60
    assert {"credential_form_new_domain", "brand_domain_mismatch", "shortener_or_redirects"} <= {f["rule"] for f in v.fired}


def test_money_request_is_critical():
    s = regex_extract("Mamá soy Daniel, necesito $2,000 por transferencia para la fianza, urgente. No le digas a nadie")
    v = rules.evaluate(s, {"saved": False}, None, 0, "es")
    assert s["money_request"]["amount"] == 2000 and s["money_request"]["method"] == "wire"
    assert v.critical


def test_trusted_family_chat_is_safe():
    s = regex_extract("Mamá, salgo del trabajo a las 6, ¿quieres que pase por tortillas?")
    assert rules.evaluate(s, {"saved": True, "trusted": True}, None, 0, "es").label == "safe"


def test_official_domain_lowers_score():
    s = regex_extract("Keystone Bank: your statement is ready")
    det = {**DET, "official_domain": True, "form_fields": [], "redirects": []}
    assert rules.evaluate(s, {"saved": False}, det, 0, "en").label == "safe"


def test_herd_match_alone_is_scam():
    assert rules.evaluate({}, {"saved": False}, None, 1, "en").label == "scam"


def test_scrub_removes_cards_and_codes():
    out = scrub("tarjeta 4111 1111 1111 1111 y su código 482913")
    assert "4111" not in out and "482913" not in out


def test_guardian_texts_never_ask_for_codes_or_money():
    from app.i18n import T
    for key, langs in T.items():
        for text in langs.values():
            assert not asks_for_secrets(text), key


def test_policy_eval_catches_a_real_ask():
    assert asks_for_secrets("Por favor envíe el código que le llegó")
    assert not asks_for_secrets("No envíe dinero ni códigos")


def test_credential_form_on_offbrand_domain_is_scam_even_when_domain_is_old():
    s = regex_extract("Keystone Bank: Your account is locked. Verify within 24 hours: https://example.trycloudflare.com/mock/keystone/")
    det = {"final_domain": "example.trycloudflare.com", "brands": ["Keystone Bank"], "official_domain": False,
           "form_fields": ["Usuario", "Contraseña", "Número de tarjeta y CVV"], "domain_age_days": 2400, "redirects": []}
    v = rules.evaluate(s, {"saved": False}, det, 0, "en")
    assert v.label == "scam" and {"brand_domain_mismatch", "credential_form_offbrand"} <= {f["rule"] for f in v.fired}
    assert "credential_form_new_domain" not in {f["rule"] for f in v.fired}
