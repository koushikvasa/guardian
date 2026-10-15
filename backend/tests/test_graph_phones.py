import os, sys
os.environ["GUARDIAN_MOCK"] = "1"
os.environ["FAMILY_PHONE_DANIEL"] = "+1 (212) 555-7788"
os.environ["FAMILY_WHATSAPP_DANIEL"] = "+91 99999 00001"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.graph import Graph


def test_env_phone_overrides_seed_and_is_normalised():
    g = Graph()
    g.load_seed()
    assert g.person("daniel")["phone"] == "+12125557788"
    assert g.person("rosa")["phone"].endswith("0001") or os.environ.get("FAMILY_PHONE_ROSA")
    assert g.person_by_phone("212-555-7788")["id"] == "daniel"


def test_whatsapp_number_routes_and_resolves_back_to_the_member():
    g = Graph()
    g.load_seed()
    assert g.whatsapp_for("+12125557788") == "+919999900001"
    assert g.person_by_phone("whatsapp:+919999900001")["id"] == "daniel"
    assert g.whatsapp_for("+15550100005").endswith("0005")  # no WhatsApp override: unchanged
