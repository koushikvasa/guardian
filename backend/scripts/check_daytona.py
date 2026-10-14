"""Smoke test #2: can a Daytona sandbox start, reach the internet, and be deleted?
usage: python scripts/check_daytona.py"""
import sys, time
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")  # pip output can contain non-cp1252 characters on Windows
from app import config
from daytona import Daytona, DaytonaConfig

PROBE = ("import urllib.request\n"
         "for u in ('https://example.com', 'https://pypi.org/simple/', 'https://api.anchorbrowser.io'):\n"
         "    try: print(u, urllib.request.urlopen(u, timeout=8).status)\n"
         "    except Exception as e: print(u, 'ERR', e)\n")

d = Daytona(DaytonaConfig(api_key=config.DAYTONA_API_KEY))
t = time.time(); sb = d.create(); print("created", sb.id, round(time.time() - t, 1), "s")
try:
    r = sb.process.code_run(PROBE)
    print("network from sandbox:\n" + (r.result or "").strip())
    r = sb.process.exec("pip install -q playwright && python -c 'import playwright;print(\"playwright ok\")'", timeout=180)
    print((r.result or "").strip()[-200:])
finally:
    t = time.time()
    try:
        d.delete(sb)
    except AttributeError:
        sb.delete()
    print("deleted", sb.id, "in", round(time.time() - t, 2), "s")
print("If network failed: set DETONATE_MODE=local (Anchor still isolates the browser) and say so honestly in Q&A.")
