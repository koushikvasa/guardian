"""Smoke test #5: one span into Phoenix. Run `phoenix serve` first, then open http://localhost:6006"""
import sys, time
sys.path.insert(0, ".")
from app import tracing, config
assert config.PHOENIX_COLLECTOR_ENDPOINT, "set PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006"
tracing.init()
with tracing.span("smoke", hello="guardian") as s:
    s.set("ok", True)
time.sleep(2); print("sent; check project", config.PHOENIX_PROJECT)
