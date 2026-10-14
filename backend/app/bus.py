"""In-process event bus. Every state change becomes an event; the UI listens on GET /events (SSE).

Events are also appended to data/events.log.jsonl so a run can be replayed on stage (?replay=).
"""
import asyncio
import json
import time
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "data" / "events.log.jsonl"

_subscribers: set[asyncio.Queue] = set()
history: list[dict] = []


def emit(kind: str, case_id: str | None = None, **data) -> dict:
    evt = {"t": round(time.time(), 3), "kind": kind, "case": case_id, **data}
    history.append(evt)
    del history[:-500]
    try:
        LOG.parent.mkdir(exist_ok=True)
        with LOG.open("a") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    except Exception:
        pass
    for q in list(_subscribers):
        q.put_nowait(evt)
    print(f"[event] {kind:<28} {case_id or '':<10} {json.dumps(data, ensure_ascii=False)[:160]}")
    return evt


async def subscribe(since: float = 0.0):
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.add(q)
    try:
        for evt in history:
            if evt["t"] > since:
                yield evt
        while True:
            try:
                yield await asyncio.wait_for(q.get(), timeout=15)
            except asyncio.TimeoutError:
                yield {"kind": "ping", "t": time.time()}
    finally:
        _subscribers.discard(q)
