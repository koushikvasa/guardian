"""Smoke test #6: Bedrock signal extraction on the demo messages."""
import json, sys
sys.path.insert(0, ".")
from app.signals import extract
from app.main import DEMO
for beat, d in DEMO.items():
    print(beat, json.dumps(extract(d["es"]), ensure_ascii=False))
