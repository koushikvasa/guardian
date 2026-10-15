"""The case engine: one forwarded message -> one case -> one trace.

  open case + ack -> scrub -> extract signals -> herd check -> detonate link (Hero 3)
  -> deterministic verdict -> route:
       money request          -> Money Second Key (Hero 2)
       claims to be family    -> Verify-by-callback (Hero 1)
       otherwise              -> text verdict, warning call if scam
  -> teach-back -> help voice note -> live evals -> fingerprints into the herd graph
  -> remember the verdict (SurrealDB Agent Memory), recalled with a trace on the next case

Guardian never approves money on its own and never asks for codes, passwords or payments.
"""
import asyncio
import hashlib
import os
import itertools
import re
import time

from . import bus, calls, config, live_evals, rules, sms
from .detonate import detonate
from .graph import graph, norm_phone
from .i18n import t
from .memory import memory
from .scrub import scrub
from .signals import detect_lang, embed, extract
from .tracing import span

cases: dict[str, dict] = {}
_key_waiters: dict[str, asyncio.Future] = {}
_ids = itertools.count(2041)


def _fingerprints(signals: dict, det: dict | None, text: str) -> list[str]:
    fps = []
    if det and det.get("final_domain"):
        fps.append("domain:" + det["final_domain"].lower())
    for u in signals.get("urls", []):
        fps.append("url:" + re.sub(r"^https?://", "", u.lower()).split("?")[0])
    norm = re.sub(r"[\d\W]+", " ", text.lower()).strip()
    fps.append("text:" + hashlib.sha1(norm.encode()).hexdigest()[:16])
    return fps


def _phrase(protected: dict) -> str:
    return protected.get("safe_phrase") or graph.family().get("safe_phrase", "")


def _who(from_phone: str, body: str, protected_id: str | None) -> dict:
    """Which protected member sent this? Explicit id > unique phone > language of the text (shared phone) > first."""
    if protected_id and graph.person(protected_id):
        return graph.person(protected_id)
    cands = [m for m in graph.people_by_phone(from_phone) if m.get("role") == "protected"]
    if len(cands) > 1:
        want = detect_lang(body)
        cands = [m for m in cands if m.get("lang") == want] or cands
    return cands[0] if cands else graph.by_role("protected")[0]


async def handle_message(from_phone: str, body: str, original_sender: str | None = None, protected_id: str | None = None,
                         quiet: bool = False) -> dict:
    """quiet=True for auto-forwarded texts: Guardian only speaks up when something is wrong, never on a harmless text."""
    protected = _who(from_phone, body, protected_id)
    lang = protected.get("lang") or detect_lang(body)
    case_id = f"A-{next(_ids)}"
    case = {"id": case_id, "protected": protected["id"], "lang": lang, "status": "open", "quiet": quiet,
            "opened_at": time.time(), "text": scrub(body), "outbound": []}
    cases[case_id] = case

    with span("case", case=case_id, lang=lang) as root:
        bus.emit("case.opened", case_id, protected=protected["name"], text=case["text"], lang=lang, quiet=quiet)
        if not quiet:
            await _sms(case, protected["phone"], t("ack", lang), key="ack")

        signals = await asyncio.to_thread(extract, case["text"])
        case["signals"] = signals
        bus.emit("signals", case_id, signals=signals)

        sender = graph.sender_context(original_sender or "", protected["id"]) if original_sender else {"saved": False, "trusted": False}
        case["sender"] = {k: v for k, v in sender.items() if k != "person"}

        # Memory recall runs alongside the sandbox so it never delays the call (the text already holds the link/claim)
        recall_task = asyncio.create_task(asyncio.to_thread(memory.recall_for_case, case, None))

        det = None
        if signals.get("urls"):
            bus.emit("detonation.started", case_id, url=signals["urls"][0])
            det = await detonate(signals["urls"][0], case_id)
            case["detonation"] = det
            bus.emit("detonation.result", case_id, **det)

        # What Guardian remembers about this link / sender / story (typed facts + retrieval trace)
        try:
            recalled = await asyncio.wait_for(recall_task, timeout=config.MEMORY_RECALL_TIMEOUT_S)
        except asyncio.TimeoutError:
            recalled = {"hits": [], "trace_id": None, "tier": "timeout"}
            bus.emit("memory.error", case_id, op="recall", error=f"timed out after {config.MEMORY_RECALL_TIMEOUT_S}s")
        prior = memory.prior_scam(recalled["hits"], signals, det, original_sender, sender)
        case["memory"] = {**recalled, "prior_scam": prior}
        bus.emit("memory.recalled", case_id, **case["memory"])

        fps = _fingerprints(signals, det, case["text"])
        herd = graph.herd_hits(fps)
        vec = await asyncio.to_thread(embed, case["text"])
        similar = await asyncio.to_thread(graph.similar_scams, vec)
        if similar:
            herd += len(similar)
            bus.emit("herd.similar", case_id, matches=[{"case": str(m["id"]), "sim": round(m["sim"], 2)} for m in similar])
        v = rules.evaluate(signals, sender, det, herd, lang, memory=prior)
        case["verdict"] = {"score": v.score, "label": v.label, "critical": v.critical, "fired": v.fired, "reasons": v.reasons(), "herd": herd}
        bus.emit("verdict", case_id, **case["verdict"])
        root.set("verdict", v.label)
        root.set("score", v.score)

        money = signals.get("money_request")
        tasks = []
        if money and (v.critical or (money.get("amount") or 0) >= graph.family().get("second_key_threshold_usd", 500)):
            tasks.append(second_key(case, protected, money))
        elif signals.get("claims_family") and not sender.get("saved"):
            tasks.append(verify_by_callback(case, protected, signals.get("claimed_name")))
        if tasks:
            await asyncio.gather(*tasks)
        else:
            await text_verdict(case, protected, v)

        if case["verdict"]["label"] == "scam":
            await asyncio.to_thread(graph.record_case, {k: case[k] for k in ("id", "protected", "lang", "text", "verdict")}, fps)
            await asyncio.to_thread(graph.store_scam_text, case_id, case["text"], vec)
            bus.emit("herd.recorded", case_id, fingerprints=len(fps))
            await asyncio.to_thread(memory.remember_verdict, case, det, original_sender, protected["name"])

        case["evals"] = live_evals.run(case, case["outbound"])
        bus.emit("eval.live", case_id, **case["evals"])
        case["status"] = "closed"
        case["time_to_call_s"] = case.get("time_to_call_s")
        bus.emit("case.closed", case_id, label=case["verdict"]["label"], time_to_call_s=case.get("time_to_call_s"))
        return case


async def _sms(case: dict, to: str, body: str, key: str = ""):
    case["outbound"].append(body)
    await sms.send(case["id"], to, body, key=key)


# ---------------- text-only route ----------------
async def text_verdict(case, protected, v):
    lang = case["lang"]
    if v.label == "safe":
        if case.get("quiet"):
            return  # auto-forwarded and harmless: say nothing
        reason = next((f["reason"] for f in v.fired if f["weight"] < 0), "")
        await _sms(case, protected["phone"], t("safe", lang, reason=reason), key="safe")
    elif v.label == "suspicious":
        await _sms(case, protected["phone"], t("suspicious", lang, reasons=" ".join(v.reasons()[:2])), key="suspicious")
    else:
        await _sms(case, protected["phone"], t("scam_calling", lang), key="scam_calling")
        await warning_call(case, protected)


# ---------------- Hero 1: verify-by-callback ----------------
async def verify_by_callback(case, protected, claimed_name):
    lang = case["lang"]
    contacts = graph.contacts_for_claim(claimed_name)
    if not contacts:
        return
    first = contacts[0]
    await _sms(case, protected["phone"], t("hold_money", lang, name=first["name"]), key="hold_money")
    attempts = [first, first] + contacts[1:]
    for i, who in enumerate(attempts):
        if i == 1:
            bus.emit("verify.retry_scheduled", case["id"], in_s=config.VERIFY_RETRY_AFTER_S)
            await asyncio.sleep(config.VERIFY_RETRY_AFTER_S)
        _mark_first_call(case)
        res = await calls.place_call(
            "verify", case["id"], who["phone"], config.VERIFY_AGENT_ID,
            {"relative_name": who["name"], "protected_name": protected["name"],
             "claim_summary": _claim_summary(case), "safe_phrase": _phrase(protected)},
            mock_script=[
                ("agent", f"Hi {who['name']}, this is Guardian calling for your mom, {protected['name']}. Quick check, it'll take 20 seconds."),
                ("agent", "Someone texting from an unknown number says they're you and need bail money. Did you contact her today?"),
                ("user", "What? No. I'm at work right now. That's not me."),
                ("agent", "Thank you. I'll tell her it was a scam and not to send anything. She's safe."),
            ],
            mock_result={"status": "completed" if config.MOCK_VERIFY_OUTCOME != "no_answer" else "no_answer",
                         "data": {"outcome": config.MOCK_VERIFY_OUTCOME}},
        )
        if res["status"] != "completed":
            await _sms(case, protected["phone"], t("verify_no_answer", lang, name=who["name"]), key="verify_no_answer")
            continue
        outcome = (res["data"].get("outcome") or "unclear").lower()
        bus.emit("verify.outcome", case["id"], outcome=outcome, relative=who["name"])
        if outcome == "denied":
            _force_scam(case, "verify_denied")
            await _sms(case, protected["phone"], t("verify_denied", lang, name=who["name"]), key="verify_denied")
            await warning_call(case, protected)
        elif outcome == "confirmed":
            await _sms(case, protected["phone"], t("verify_confirmed", lang, name=who["name"]), key="verify_confirmed")
        return
    bus.emit("verify.exhausted", case["id"])


# ---------------- Hero 2: Money Second Key ----------------
async def second_key(case, protected, money):
    lang = case["lang"]
    guardian = graph.by_role("guardian")[0]
    amount = int(money.get("amount") or 0)
    case["money"] = {"amount": amount, "method": money.get("method"), "state": "locked"}
    bus.emit("money.locked", case["id"], amount=amount, method=money.get("method"), guardian=guardian["name"],
             reasons=case["verdict"]["reasons"])
    await _sms(case, protected["phone"], t("key_waiting", lang, amount=f"{amount:,}", guardian=guardian["name"]), key="key_waiting")
    link = f"{config.PUBLIC_BASE_URL.rstrip('/')}/key/{case['id']}"
    await sms.send(case["id"], guardian["phone"], f"Guardian: {protected['name']} wants to send ${amount:,}. Your key is needed: {link}", role="guardian", key="key_link")

    fut = asyncio.get_running_loop().create_future()
    _key_waiters[case["id"]] = fut
    _mark_first_call(case)
    call_task = asyncio.create_task(calls.place_call(
        "second_key", case["id"], guardian["phone"], config.SECOND_KEY_AGENT_ID,
        {"guardian_name": guardian["name"], "protected_name": protected["name"], "amount": f"${amount:,}",
         "method": money.get("method") or "", "reasons": " ".join(case["verdict"]["reasons"]), "key_link": link,
         "language": {"es": "Spanish", "te": "Telugu"}.get(lang, "English")},
        mock_script=[
            ("agent", f"Hi {guardian['name']}, it's Guardian. Your mom wants to send ${amount:,} by wire. She was told it's bail for you."),
            ("agent", "It came from an unknown number, asked her to keep it secret, and a wire can't be undone."),
            ("user", "That's not me. Don't let her send it."),
            ("agent", "Understood. Tap Don't send it in the app and I'll tell her in Spanish right now."),
        ],
        mock_result={"status": "completed", "data": {"decision": "decline"}},
    ))
    if config.MOCK_KEY_DECISION:
        async def auto():
            await call_task
            if not fut.done():
                fut.set_result(config.MOCK_KEY_DECISION)
        asyncio.create_task(auto())

    async def verbal_decline():
        res = await call_task
        if (res.get("data") or {}).get("decision") == "decline" and not fut.done():
            fut.set_result("decline")  # a spoken "don't send" is enough to keep it locked; approval needs the app
    if os.environ.get("KEY_ACCEPT_VERBAL", "0") == "1":  # off for the stage: Daniel's button is the beat
        asyncio.create_task(verbal_decline())

    decision = await fut  # no timeout: money stays locked until a human key turns
    _key_waiters.pop(case["id"], None)
    case["money"]["state"] = "declined" if decision == "decline" else "approved"
    bus.emit("key.decision", case["id"], decision=decision, by=guardian["name"])
    if decision == "decline":
        _force_scam(case, "second_key_declined")
        await _sms(case, protected["phone"], t("key_declined", lang, guardian=guardian["name"]), key="key_declined")
        await warning_call(case, protected)
    else:
        await _sms(case, protected["phone"], t("key_approved", lang, guardian=guardian["name"]), key="key_approved")


def turn_key(case_id: str, decision: str) -> bool:
    fut = _key_waiters.get(case_id)
    if not fut or fut.done() or decision not in ("approve", "decline"):
        return False
    fut.set_result(decision)
    return True


# ---------------- warning call + teach-back + help note ----------------
async def warning_call(case, protected):
    if case.get("warned"):
        return
    case["warned"] = True
    lang = case["lang"]
    phrase = _phrase(protected)
    name = protected["name"]
    reasons = case["verdict"]["reasons"][:3]
    _mark_first_call(case)
    agent = {"es": config.WARNING_AGENT_ID_ES, "en": config.WARNING_AGENT_ID_EN, "te": config.WARNING_AGENT_ID_TE}.get(lang) or config.WARNING_AGENT_ID_EN
    if lang == "es":
        script = [("agent", f"{name}, soy Guardian. Su frase de familia es “{phrase}”."),
                  ("agent", "El mensaje que me envió es una estafa."),
                  ("agent", "No toque el enlace, no conteste y no envíe dinero."),
                  ("agent", "Hizo muy bien en mandármelo. Usted está a salvo."),
                  ("agent", "¿Qué va a hacer si le vuelven a escribir?"),
                  ("user", "Se lo mando a usted primero y no toco nada."),
                  ("agent", f"Exacto. Muy bien, {name}.")]
    elif lang == "te":
        script = [("agent", f"{name}, నేను Guardian ని. మీ కుటుంబ పదం “{phrase}”."),
                  ("agent", "మీరు నాకు పంపిన మెసేజ్ మోసం."),
                  ("agent", "లింక్ నొక్కొద్దు, జవాబు ఇవ్వొద్దు, డబ్బు పంపొద్దు."),
                  ("agent", "నాకు పంపడం చాలా మంచి పని చేశారు. మీరు సురక్షితంగా ఉన్నారు."),
                  ("agent", "మళ్ళీ మెసేజ్ వస్తే మీరు ఏం చేస్తారు?"),
                  ("user", "ముందు మీకు పంపుతాను, ఏదీ నొక్కను."),
                  ("agent", "సరిగ్గా చెప్పారు. చాలా బాగుంది.")]
    else:
        script = [("agent", f"{name}, it's Guardian. Your family phrase is “{phrase}”."),
                  ("agent", "The message you sent me is a scam. Don't tap the link, don't reply, don't send money."),
                  ("agent", "You did the right thing sending it to me. You're safe."),
                  ("agent", "What will you do if they text you again?"),
                  ("user", "Send it to you first and not touch anything."),
                  ("agent", "Exactly. Well done.")]
    res = await calls.place_call(
        "warning", case["id"], protected["phone"], agent,
        {"name": name, "safe_phrase": phrase, "reasons": " ".join(reasons),
         "verdict": {"es": "estafa", "te": "మోసం"}.get(lang, "scam")},
        mock_script=script,
        mock_result={"status": "completed", "data": {"teach_back_ok": True}},
    )
    ok = bool((res.get("data") or {}).get("teach_back_ok"))
    bus.emit("teachback", case["id"], ok=ok)
    await help_note(case, protected)


async def help_note(case, protected):
    lang = case["lang"]
    money = case.get("money", {}).get("amount")
    steps = _story_steps(case, lang, money)
    audio = await _tts(" ".join(steps), case["id"], lang)
    link = f"{config.PUBLIC_BASE_URL.rstrip('/')}/help/{case['id']}"
    case["help"] = {"title": _help_title(lang, money), "steps": steps, "audio_url": audio, "name": protected["name"]}
    bus.emit("help.note.ready", case["id"], steps=steps, audio_url=audio, title=case["help"]["title"], link=link)
    await _sms(case, protected["phone"], t("help_note", lang, link=link), key="help_note")


def _help_title(lang, money):
    if lang == "es":
        return f"Casi me roban ${money:,}" if money else "Casi caigo en una estafa"
    if lang == "te":
        return f"${money:,} పోయేవి, తప్పించుకున్నాను" if money else "మోసం నుంచి తప్పించుకున్నాను"
    return f"I almost lost ${money:,}" if money else "I almost fell for a scam"


def _story_steps(case, lang, money):
    kind = "family" if case["signals"].get("claims_family") else "link"
    if lang == "te":
        if kind == "family":
            return ["ఎవరో నా కొడుకునని చెప్పి డబ్బు అడిగారు.", "Guardian నా అసలు కొడుకుకి కాల్ చేసింది. అతను బాగానే ఉన్నాడు.", "అది మోసం. నేను ఏమీ పంపలేదు."]
        return ["బ్యాంక్ నుంచి అని లింక్‌తో మెసేజ్ వచ్చింది.", "Guardian దాన్ని సురక్షితమైన చోట తెరిచింది: అది నకిలీ పేజీ.", "నేను ఏదీ నొక్కలేదు. మీకూ వస్తే, తెరవొద్దు."]
    if lang == "es":
        if kind == "family":
            return ["Me escribió alguien diciendo que era mi hijo, pidiendo dinero.",
                    "Guardian llamó a mi hijo de verdad. Estaba bien.", "Era una estafa. No envié nada."]
        return ["Me llegó un mensaje del banco con un enlace.", "Guardian lo abrió en un lugar seguro: era una página falsa.", "No toqué nada. Si le llega uno, no lo abra."]
    if kind == "family":
        return ["Someone texted pretending to be my son, asking for money.", "Guardian called my real son. He was fine.", "It was a scam. I didn't send anything."]
    return ["I got a bank text with a link.", "Guardian opened it somewhere safe: it was a fake page.", "I didn't tap anything. If you get one, don't open it."]


async def _tts(text: str, case_id: str, lang: str) -> str | None:
    import os
    voice = os.environ.get({"es": "ELEVENLABS_VOICE_ID_ES", "te": "ELEVENLABS_VOICE_ID_TE"}.get(lang, "ELEVENLABS_VOICE_ID_EN"), "") or os.environ.get("ELEVENLABS_VOICE_ID_EN", "")
    if not (config.live(config.ELEVENLABS_API_KEY) and voice):
        return None
    import httpx
    from pathlib import Path
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                             headers={"xi-api-key": config.ELEVENLABS_API_KEY},
                             json={"text": text, "model_id": "eleven_v3" if lang == "te" else "eleven_multilingual_v2"})  # multilingual_v2 has no Telugu
            r.raise_for_status()
        p = Path(__file__).resolve().parent.parent / "data" / "notes"
        p.mkdir(parents=True, exist_ok=True)
        (p / f"{case_id}.mp3").write_bytes(r.content)
        return f"/notes/{case_id}.mp3"
    except Exception as e:
        bus.emit("tts.error", case_id, error=str(e))
        return None


# ---------------- helpers ----------------
def _mark_first_call(case):
    if case.get("time_to_call_s") is None:
        case["time_to_call_s"] = round(time.time() - case["opened_at"], 1)


def _force_scam(case, why):
    v = case["verdict"]
    if v["label"] != "scam":
        v["label"] = "scam"
        v["confirmed_by"] = why
        bus.emit("verdict", case["id"], **v)


def _claim_summary(case) -> str:
    s = case["signals"]
    m = s.get("money_request") or {}
    bits = [f"claims to be {s.get('claimed_name') or 'a relative'}"]
    if m:
        bits.append(f"asks for ${int(m.get('amount') or 0):,} by {m.get('method')}")
    if s.get("secrecy"):
        bits.append("asked to keep it secret")
    return ", ".join(bits)


__all__ = ["handle_message", "turn_key", "cases", "norm_phone"]
