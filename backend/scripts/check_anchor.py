"""Smoke test #3: Anchor session + screenshot via the same job Daytona runs.
usage: python scripts/check_anchor.py [url]"""
import json, os, subprocess, sys
sys.path.insert(0, ".")
from app import config
url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
env = {**os.environ, "TARGET_URL": url, "ANCHOR_API_KEY": config.ANCHOR_API_KEY, "TIMEOUT_S": "20"}
p = subprocess.run([sys.executable, "-I", "app/sandbox_job.py"], env=env, capture_output=True, text=True)
line = [l for l in p.stdout.splitlines() if l.startswith("GUARDIAN_RESULT ")]
res = json.loads(line[-1][16:]) if line else {"error": p.stderr[-800:]}
res.pop("screenshot_b64", None)
print(json.dumps(res, indent=2, ensure_ascii=False))
