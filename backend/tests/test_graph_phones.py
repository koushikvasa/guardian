import os, sys
os.environ["GUARDIAN_MOCK"] = "1"
os.environ["FAMILY_PHONE_DANIEL"] = "+1 (212) 555-7788"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.graph import Graph


def test_env_phone_overrides_seed_and_is_normalised():
    g = Graph()
    g.load_seed()
    assert g.person("daniel")["phone"] == "+12125557788"
    assert g.person("rosa")["phone"].endswith("0001") or os.environ.get("FAMILY_PHONE_ROSA")
    assert g.person_by_phone("212-555-7788")["id"] == "daniel"
