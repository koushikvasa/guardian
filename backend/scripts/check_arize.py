"""Smoke test #5: one trace + one tiny experiment land in Arize AX.
usage: python scripts/check_arize.py   (needs ARIZE_SPACE_ID + ARIZE_API_KEY)"""
import subprocess, sys, time
sys.path.insert(0, ".")
from app import config, tracing

assert config.live(config.ARIZE_SPACE_ID, config.ARIZE_API_KEY), "set ARIZE_SPACE_ID and ARIZE_API_KEY"
tracing.init()
assert tracing._tracer is not None, "tracing did not initialise (see message above)"
with tracing.span("check.arize", case="smoke") as s:
    with tracing.span("check.child", step=1):
        time.sleep(0.2)
    s.set("ok", True)
tracing.flush()
print("trace sent -> app.arize.com -> project", config.ARIZE_PROJECT, "(may take ~30s to appear)")
print("now running the offline eval, which logs a dataset + experiment ...")
sys.exit(subprocess.call([sys.executable, "evals/run_eval.py"]))
