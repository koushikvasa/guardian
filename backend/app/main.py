"""Guardian API.

  POST /sms                    Twilio inbound SMS/MMS webhook (Rosa forwards a message)
  GET  /events                 server-sent events for every stage + phone screen
  GET  /cases, /cases/{id}     case state
  POST /cases/{id}/key         Daniel's second key: {"decision": "approve"|"decline"}
  POST /webhooks/elevenlabs    ElevenLabs post-call webhook (optional; polling also works)
  GET  /family, POST /family   setup screen
  GET  /scoreboard             Arize eval numbers for the stage scoreboard
  POST /demo/{link|family|money}  fire a demo beat without a phone
  GET  /health                 which sponsors are live vs mock
"""
import asyncio
import json
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import bus, calls, config, pipeline, tracing
from .graph import graph
from .memory import memory

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Guardian")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for sub in ("shots", "notes"):
    (ROOT / "data" / sub).mkdir(parents=True, exist_ok=True)
    app.mount(f"/{sub}", StaticFiles(directory=ROOT / "data" / sub), name=sub)
app.mount("/mock", StaticFiles(directory=ROOT / "mock_sites", html=True), name="mock")

DEMO = {
    "link": {"es": "Banco Keystone: Su cuenta está bloqueada. Verifique en 24 horas: bit.ly/kst-verif",
             "en": "Keystone Bank: Your account is locked. Verify within 24 hours: bit.ly/kst-verif"},
    "family": {"es": "Mamá soy Daniel, choqué el carro y estoy detenido. Te llamo de otro número, no le digas a nadie por favor",
               "en": "Mom it's me Daniel, I crashed the car and I'm in jail. Calling from a friend's phone, please don't tell anyone"},
    "money": {"es": "Mamá soy Daniel, necesito $2,000 por transferencia para la fianza en Tijuana, urgente. No le digas a nadie",
              "en": "Mom it's me Daniel, I need $2,000 by wire for bail in Tijuana, urgent. Don't tell anyone"},
}


@app.on_event("startup")
async def startup():
    tracing.init()
    graph.load_seed()
    asyncio.create_task(asyncio.to_thread(memory.seed_family, graph.family()))  # once per memory context
    print("[guardian] sponsors live:", json.dumps(config.status()))


@app.get("/health")
async def health():
    return {"ok": True, "live": config.status(), "mock_forced": config.FORCE_MOCK}


@app.post("/sms")
async def inbound_sms(request: Request, bg: BackgroundTasks):
    form = await request.form()
    body = form.get("Body", "")
    from_ = form.get("From", "")
    # Optional: "De: +16195550199" line tells us who originally sent it
    orig = None
    for line in body.splitlines():
        if line.lower().startswith(("de:", "from:")):
            orig = line.split(":", 1)[1].strip()
    if int(form.get("NumMedia", 0) or 0) > 0:
        bg.add_task(_with_ocr, from_, body, form.get("MediaUrl0"), orig)
    else:
        bus.emit("sms.in", None, frm=from_, body=body)
        bg.add_task(pipeline.handle_message, from_, body, orig)
    # empty TwiML: the ack goes out from the pipeline in the right language
    return Response('<?xml version="1.0" encoding="UTF-8"?><Response/>', media_type="application/xml")


async def _with_ocr(from_, body, media_url, orig):
    import httpx

    from .signals import ocr_image

    text = body
    try:
        async with httpx.AsyncClient(timeout=15, auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)) as c:
            img = (await c.get(media_url, follow_redirects=True)).content
        text = (body + "\n" + await asyncio.to_thread(ocr_image, img)).strip()
    except Exception as e:
        bus.emit("ocr.error", None, error=str(e))
    bus.emit("sms.in", None, frm=from_, body=text)
    await pipeline.handle_message(from_, text, orig)


@app.post("/ingest")
async def ingest(payload: dict, bg: BackgroundTasks):
    """Auto-forward from Rosa's phone (iOS Shortcuts message automation / Android app).
    Body: {"token": INGEST_TOKEN, "phone": rosa's number, "sender": who texted her, "text": the message}"""
    import os
    if payload.get("token") != os.environ.get("INGEST_TOKEN", "dev-token"):
        return JSONResponse({"error": "bad token"}, 401)
    sender, text = payload.get("sender", ""), payload.get("text", "")
    # Android sends the notification title (a contact NAME when saved); iPhone sends the number.
    is_family = graph.person_by_phone(sender) or any(m["name"].lower() == sender.strip().lower() for m in graph.family()["members"])
    if is_family:  # family texting Rosa: never inspected
        return {"ok": True, "skipped": "family"}
    rosa = graph.by_role("protected")[0]
    bus.emit("sms.in", None, frm=sender, body=text, via="auto")
    bg.add_task(pipeline.handle_message, payload.get("phone") or rosa["phone"], text, sender or None)
    return {"ok": True}


@app.get("/events")
async def events(request: Request, since: float = 0.0):
    # EventSource reconnects on its own (App Runner / proxies cut long requests) and sends Last-Event-ID
    since = max(since, float(request.headers.get("last-event-id") or 0))

    async def gen():
        async for evt in bus.subscribe(since):
            yield f"id: {evt['t']}\ndata: {json.dumps(evt, ensure_ascii=False)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/events/log")
async def events_log():
    return bus.history


@app.get("/cases")
async def list_cases():
    return [_public(c) for c in pipeline.cases.values()]


@app.get("/cases/{case_id}")
async def get_case(case_id: str):
    c = pipeline.cases.get(case_id)
    return _public(c) if c else JSONResponse({"error": "not found"}, 404)


@app.post("/cases/{case_id}/key")
async def key(case_id: str, payload: dict):
    ok = pipeline.turn_key(case_id, payload.get("decision", ""))
    return {"ok": ok}


@app.post("/webhooks/elevenlabs")
async def el_webhook(request: Request):
    # TODO before Friday if you expose this publicly: verify the ElevenLabs-Signature HMAC header.
    calls.resolve_from_webhook(await request.json())
    return {"ok": True}


@app.get("/family")
async def get_family():
    return graph.family()


@app.post("/family")
async def set_family(payload: dict):
    p = ROOT / "data" / "seed_family.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    graph.load_seed(p)
    return {"ok": True}


@app.get("/scoreboard")
async def scoreboard():
    p = ROOT / "data" / "scoreboard.json"
    base = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    live = [c for c in pipeline.cases.values() if c.get("status") == "closed"]
    ttc = [c["time_to_call_s"] for c in live if c.get("time_to_call_s") is not None]
    base["live"] = {
        "cases": len(live),
        "median_time_to_call_s": sorted(ttc)[len(ttc) // 2] if ttc else None,
        "evals_passed": sum(all(c.get("evals", {}).values()) for c in live),
    }
    return base


@app.post("/demo/{beat}")
async def demo(beat: str, bg: BackgroundTasks, lang: str = "es"):
    if beat not in DEMO:
        return JSONResponse({"error": f"beat must be one of {list(DEMO)}"}, 400)
    rosa = graph.by_role("protected")[0]
    text = DEMO[beat][lang if lang in ("es", "en") else "es"]
    bus.emit("sms.in", None, frm=rosa["phone"], body=text)
    bg.add_task(pipeline.handle_message, rosa["phone"], text, "+16195550199" if beat != "link" else None)
    return {"ok": True, "beat": beat, "text": text}


def _public(c: dict) -> dict:
    return {k: v for k, v in c.items() if k not in ("outbound",)}
