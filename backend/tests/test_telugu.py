import os, sys
os.environ["GUARDIAN_MOCK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import i18n, rules
from app.graph import Graph
from app.live_evals import asks_for_secrets
from app.signals import detect_lang, regex_extract

TE_MONEY = "అమ్మా నేను Daniel, బెయిల్ కోసం అర్జెంట్‌గా $2,000 wire పంపు. ఎవరికీ చెప్పొద్దు"
TE_LINK = "Keystone Bank: మీ ఖాతా బ్లాక్ అయింది. 24 గంటల్లో ధృవీకరించండి: bit.ly/kst-verif"


def test_telugu_script_is_detected():
    assert detect_lang(TE_MONEY) == "te" and detect_lang("Mom it's me, send money") == "en"


def test_telugu_money_text_yields_the_same_signals_as_spanish():
    s = regex_extract(TE_MONEY)
    assert s["claims_family"] and s["claimed_name"] == "Daniel"
    assert s["money_request"] == {"amount": 2000.0, "method": "wire"}
    assert s["secrecy"] and s["urgency"] and s["language"] == "te"
    v = rules.evaluate(s, {"saved": False}, None, 0, "te")
    assert v.critical and any("ఀ" <= ch <= "౿" for r in v.reasons() for ch in r)  # reasons in Telugu script


def test_telugu_link_text_has_brand_and_urgency():
    s = regex_extract(TE_LINK)
    assert s["brand"] == "Keystone Bank" and s["urgency"] and s["shortener"] and s["urls"] == ["bit.ly/kst-verif"]


def test_every_sms_string_exists_in_telugu_and_asks_for_nothing():
    for key, variants in i18n.T.items():
        assert "te" in variants, key
        txt = i18n.t(key, "te", name="Daniel", reason="", reasons="", amount="2,000", guardian="Daniel", link="x")
        assert txt.startswith("Guardian:") and not asks_for_secrets(txt), key


def test_every_rule_has_telugu_text():
    for rule, (_, texts) in rules.RULES.items():
        assert "te" in texts, rule


def test_two_protected_members_with_their_own_phrases():
    g = Graph()
    g.load_seed()
    assert g.protected_for_lang("te")["name"] == "Amma" and g.protected_for_lang("te")["safe_phrase"].lower() == "kanna"
    assert g.protected_for_lang("en")["name"] == "Jasmine" and g.protected_for_lang("en")["safe_phrase"] == "Buckie the dog"
    assert g.protected_for_lang("es")["name"] == "Rosa"
