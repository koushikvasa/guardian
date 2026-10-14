import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pathlib import Path
from app.quarantine_job import analyze

KEYSTONE = Path(__file__).resolve().parent.parent / "mock_sites" / "keystone" / "index.html"


def test_keystone_page_parses_to_credential_form_on_wrong_domain():
    html = KEYSTONE.read_text(encoding="utf-8")
    r = analyze({"html": html, "title": "Keystone Bank | Verifique su cuenta", "final_url": "https://keystone-verifica.top/login", "target": "bit.ly/kst-verif"})
    assert r["final_domain"] == "keystone-verifica.top" and r["brands"] == ["Keystone Bank"] and r["official_domain"] is False
    assert r["asks_credentials"] and any("contraseña" in f.lower() or "pass" in f.lower() for f in r["form_fields"])


def test_official_domain_is_recognised_and_scripts_dropped_from_text():
    r = analyze({"html": "<html><head><script>alert(1)</script></head><body><h1>Welcome to Chase</h1><a href='/x.exe'>get</a></body></html>",
                 "title": "Chase", "final_url": "https://secure.chase.com/", "target": "chase.com"})
    assert r["official_domain"] and "alert" not in r["text_excerpt"] and r["download_links"] == ["/x.exe"]
