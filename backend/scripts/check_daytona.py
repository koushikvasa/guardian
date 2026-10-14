"""Smoke test #2: can a Daytona sandbox start, reach the internet, and be deleted?"""
import sys, time
sys.path.insert(0, ".")
from app import config
from daytona import Daytona, DaytonaConfig

d = Daytona(DaytonaConfig(api_key=config.DAYTONA_API_KEY))
t = time.time(); sb = d.create(); print("created", sb.id, round(time.time() - t, 1), "s")
r = sb.process.code_run("import urllib.request;print(urllib.request.urlopen('https://api.anchorbrowser.io',timeout=8).status)")
print("network from sandbox:", r.result.strip() or r)
r = sb.process.exec("pip install -q playwright==1.48.0 && python -c 'import playwright;print(\"playwright ok\")'", timeout=180)
print(r.result.strip()[-200:])
t = time.time()
try: d.delete(sb)
except AttributeError: sb.delete()
print("deleted in", round(time.time() - t, 2), "s")
print("If network failed: set DETONATE_MODE=local (Anchor still isolates the browser) and say so honestly in Q&A.")
