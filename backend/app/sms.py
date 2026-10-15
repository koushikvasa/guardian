"""Twilio text out. Mock mode only emits the event (the phone screens show it either way).

Channel: WhatsApp when TWILIO_WHATSAPP_FROM is set (delivers immediately, no A2P 10DLC registration),
otherwise SMS from TWILIO_FROM (an unregistered US local number is blocked with error 30034).

Budget: TEXT_BUDGET caps how many real texts leave the building (sandbox WhatsApp has a monthly quota);
TEXT_ESSENTIAL_ONLY=1 sends only the texts no call covers. Every text is still shown on the screens.
"""
import asyncio
import json
from pathlib import Path

import httpx

from . import bus, config
from .graph import graph

# Texts a phone call does not already cover (the alert that a call is coming, Daniel's key link, the help note,
# the only notice on a 'suspicious' verdict, and the go-ahead after an approval).
ESSENTIAL = {"scam_calling", "key_link", "help_note", "suspicious", "key_approved"}
_COUNTER = Path(__file__).resolve().parent.parent / "data" / "texts_sent.json"


def _addr(number: str) -> str:
    n = number.strip()
    if config.TWILIO_WHATSAPP_FROM:
        return n if n.startswith("whatsapp:") else f"whatsapp:{n}"
    return n[len("whatsapp:"):] if n.startswith("whatsapp:") else n


def channel() -> str:
    return "whatsapp" if config.TWILIO_WHATSAPP_FROM else "sms"


def sent_count() -> int:
    try:
        return int(json.loads(_COUNTER.read_text()).get("sent", 0))
    except Exception:
        return 0


def _bump():
    _COUNTER.parent.mkdir(parents=True, exist_ok=True)
    _COUNTER.write_text(json.dumps({"sent": sent_count() + 1}))


def budget() -> dict:
    return {"sent": sent_count(), "budget": config.TEXT_BUDGET or None, "essential_only": config.TEXT_ESSENTIAL_ONLY}


async def send(case_id: str | None, to: str, body: str, role: str = "protected", key: str = ""):
    live = config.live(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN) and bool(config.TWILIO_WHATSAPP_FROM or config.TWILIO_FROM)
    skipped = None
    if live and config.TEXT_ESSENTIAL_ONLY and key and key not in ESSENTIAL:
        skipped = "not essential"
    elif live and config.TEXT_BUDGET and sent_count() >= config.TEXT_BUDGET:
        skipped = "budget exhausted"
    bus.emit("sms.out", case_id, to=to, body=body, role=role, channel=channel(), key=key, delivered=live and not skipped, skipped=skipped)
    if not live or skipped:
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}/Messages.json"
    frm = _addr(config.TWILIO_WHATSAPP_FROM or config.TWILIO_FROM)
    dest = graph.whatsapp_for(to) if config.TWILIO_WHATSAPP_FROM else to
    try:
        r = await asyncio.to_thread(
            httpx.post, url, data={"To": _addr(dest), "From": frm, "Body": body},
            auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN), timeout=10,
        )
        if r.status_code >= 300:
            bus.emit("sms.error", case_id, error=r.text[:200], channel=channel())
        else:
            _bump()
    except Exception as e:
        bus.emit("sms.error", case_id, error=str(e), channel=channel())
