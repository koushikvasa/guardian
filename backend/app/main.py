"""Guardian API.

  POST /sms                    Twilio inbound SMS/MMS webhook (Rosa forwards a message)
  GET  /events                 server-sent events for every stage + phone screen
  GET  /cases, /cases/{id}     case state
  POST /cases/{id}/key         Daniel's second key: {"decision": "approve"|"decline"}
  POST /webhooks/elevenlabs    ElevenLabs post-call webhook (optional; polling also works)
  GET  /key/{id}               Daniel's second key page (phone-openable, through PUBLIC_BASE_URL)
  GET  /help/{id}              the help voice note as a shareable page
  GET  /family, POST /family   setup screen
  GET  /scoreboard             Arize eval numbers for the stage scoreboard
  POST /demo/{link|family|money|support}?lang=en|te|es  fire a demo beat without a phone (Jasmine / Amma / Rosa)
  GET  /health                 which sponsors are live vs mock
"""
import asyncio
import json
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import bus, calls, config, pipeline, sms, tracing
from .graph import graph
from .memory import memory
from .help_page import render as render_help
from .key_page import render as render_key

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Guardian")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for sub in ("shots", "notes"):
    (ROOT / "data" / sub).mkdir(parents=True, exist_ok=True)
    app.mount(f"/{sub}", StaticFiles(directory=ROOT / "data" / sub), name=sub)
app.mount("/mock", StaticFiles(directory=ROOT / "mock_sites", html=True), name="mock")

DEMO = {
    "link": {"es": "Banco Keystone: Su cuenta está bloqueada. Verifique en 24 horas: {link}",
             "en": "Keystone Bank: Your account is locked. Verify within 24 hours: {link}"},
    "family": {"es": "Mamá soy Daniel, choqué el carro y estoy detenido. Te llamo de otro número, no le digas a nadie por favor",
               "en": "Mom it's me Daniel, I crashed the car and I'm in jail. Calling from a friend's phone, please don't tell anyone"},
    "money": {"es": "Mamá soy Daniel, necesito $2,000 por transferencia para la fianza en Tijuana, urgente. No le digas a nadie",
              "en": "Mom it's me Daniel, I need $2,000 by wire for bail in Tijuana, urgent. Don't tell anyone"},
}
DEMO["link"]["te"] = "Keystone Bank: మీ ఖాతా బ్లాక్ అయింది. 24 గంటల్లో ధృవీకరించండి: {link}"


def demo_link() -> str:
    """Only mock_sites/keystone is ever detonated. Live: the mock page through PUBLIC_BASE_URL; mock mode: a fake short link."""
    if config.DEMO_LINK:
        return config.DEMO_LINK
    if config.live(config.ANCHOR_API_KEY) and config.DETONATE_MODE != "mock":
        return config.PUBLIC_BASE_URL.rstrip("/") + "/mock/keystone/"
    return "bit.ly/kst-verif"


def demo_text(beat: str, lang: str) -> str:
    return DEMO[beat][lang].replace("{link}", demo_link())
DEMO["family"]["te"] = "అమ్మా నేను Daniel, కారు యాక్సిడెంట్ అయింది, పోలీస్ స్టేషన్‌లో ఉన్నాను. వేరే నంబర్ నుంచి కాల్ చేస్తున్నా, ఎవరికీ చెప్పొద్దు"
DEMO["money"]["te"] = "అమ్మా నేను Daniel, బెయిల్ కోసం అర్జెంట్‌గా $2,000 wire పంపు. ఎవరికీ చెప్పొద్దు"
# The protected member reports a scam phone call in her own words (Guardian can't listen to her calls; it can act on what she tells it)
DEMO["support"] = {
    "en": "A man from Microsoft just called, says my computer has a virus. He wants me to install AnyDesk and buy $500 Google Play cards to fix it. He is waiting on the line, call back 1-888-555-0199",
    "es": "Me llamó un señor de Microsoft, dice que mi computadora tiene un virus. Quiere que instale AnyDesk y compre $500 en tarjetas de Google Play. Está esperando en la línea, llamar al 1-888-555-0199",
    "te": "Microsoft నుంచి అని ఒకాయన కాల్ చేశాడు, నా కంప్యూటర్‌లో వైరస్ ఉందంట. AnyDesk ఇన్‌స్టాల్ చేయమని, $500 Google Play కార్డులు కొనమని అంటున్నాడు. లైన్‌లో వెయిట్ చేస్తున్నాడు, 1-888-555-0199",
}


@app.on_event("startup")
async def startup():
    tracing.init()
    graph.load_seed()
    asyncio.create_task(asyncio.to_thread(memory.seed_family, graph.family()))  # once per memory context
    print("[guardian] sponsors live:", json.dumps(config.status()))


@app.get("/health")
async def health():
    return {"ok": True, "live": config.status(), "mock_forced": config.FORCE_MOCK, "texts": sms.budget(), "demo_live": config.DEMO_LIVE}


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
    await queue_ingest(payload.get("phone") or rosa["phone"], sender, text)
    return {"ok": True, "merging_for_s": config.INGEST_MERGE_S}


_pending: dict[tuple[str, str], dict] = {}


async def queue_ingest(phone: str, sender: str, text: str):
    """Carriers split a long SMS into several notifications. Collect fragments from the same sender for
    INGEST_MERGE_S seconds, then open ONE case with the joined text."""
    key = (phone, sender)
    slot = _pending.get(key)
    if slot:
        slot["texts"].append(text)
        slot["task"].cancel()
    else:
        slot = _pending[key] = {"texts": [text]}

    async def flush():
        try:
            await asyncio.sleep(config.INGEST_MERGE_S)
        except asyncio.CancelledError:
            return
        _pending.pop(key, None)
        body = " ".join(t.strip() for t in slot["texts"] if t and t.strip())
        bus.emit("sms.in", None, frm=sender, body=body, via="auto", fragments=len(slot["texts"]))
        await pipeline.handle_message(phone, body, sender or None, None, True)

    slot["task"] = asyncio.create_task(flush())


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


@app.get("/key/{case_id}")
async def key_page(case_id: str):
    """Daniel's second key, openable from the text on his phone. Approve = press-and-hold; Guardian never approves."""
    c = pipeline.cases.get(case_id)
    if not c:
        return Response("No such case.", 404, media_type="text/plain")
    return Response(render_key(_public(c), config.PUBLIC_BASE_URL.rstrip("/")), media_type="text/html; charset=utf-8")


@app.get("/help/{case_id}")
async def help_page(case_id: str):
    """The protected member's shareable story (opened from the text on any phone)."""
    c = pipeline.cases.get(case_id)
    h = (c or {}).get("help")
    if not h:
        return Response("Not ready yet.", 404, media_type="text/plain")
    audio = (config.PUBLIC_BASE_URL.rstrip("/") + h["audio_url"]) if h.get("audio_url") else None
    return Response(render_help(c, h["name"], h["title"], h["steps"], audio, c["lang"]), media_type="text/html; charset=utf-8")


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
async def demo(beat: str, bg: BackgroundTasks, lang: str = "en", dry: int = 0):
    """dry=1 rehearses the beat with every sponsor mocked for that case only: no texts, no calls, no sandbox."""
    if beat not in DEMO:
        return JSONResponse({"error": f"beat must be one of {list(DEMO)}"}, 400)
    lang = lang if lang in DEMO["link"] else "en"
    who = graph.protected_for_lang(lang)  # Jasmine (en), Amma (te), Rosa (es)
    text = demo_text(beat, lang)
    dry = 1 if (dry or not config.DEMO_LIVE) else 0  # DEMO_LIVE=0 makes every beat a rehearsal, no matter what was asked
    bus.emit("sms.in", None, frm=who["phone"], body=text, dry=bool(dry))

    async def run():
        if dry:
            config.DRY.set(True)
        await pipeline.handle_message(who["phone"], text, "+16195550199" if beat != "link" else None, who["id"])

    bg.add_task(run)
    return {"ok": True, "beat": beat, "lang": lang, "protected": who["name"], "text": text, "dry": bool(dry)}


def _public(c: dict) -> dict:
    return {k: v for k, v in c.items() if k not in ("outbound",)}
