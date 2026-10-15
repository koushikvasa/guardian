"""Twilio text out. Mock mode only emits the event (the phone screens show it either way).

Channel: WhatsApp when TWILIO_WHATSAPP_FROM is set (delivers immediately, no A2P 10DLC registration),
otherwise SMS from TWILIO_FROM (an unregistered US local number is blocked with error 30034).
"""
import asyncio

import httpx

from . import bus, config


def _addr(number: str) -> str:
    n = number.strip()
    if config.TWILIO_WHATSAPP_FROM:
        return n if n.startswith("whatsapp:") else f"whatsapp:{n}"
    return n[len("whatsapp:"):] if n.startswith("whatsapp:") else n


def channel() -> str:
    return "whatsapp" if config.TWILIO_WHATSAPP_FROM else "sms"


async def send(case_id: str | None, to: str, body: str, role: str = "protected"):
    bus.emit("sms.out", case_id, to=to, body=body, role=role, channel=channel())
    if not config.live(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN) or not (config.TWILIO_WHATSAPP_FROM or config.TWILIO_FROM):
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}/Messages.json"
    frm = _addr(config.TWILIO_WHATSAPP_FROM or config.TWILIO_FROM)
    try:
        r = await asyncio.to_thread(
            httpx.post, url, data={"To": _addr(to), "From": frm, "Body": body},
            auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN), timeout=10,
        )
        if r.status_code >= 300:
            bus.emit("sms.error", case_id, error=r.text[:200], channel=channel())
    except Exception as e:
        bus.emit("sms.error", case_id, error=str(e), channel=channel())
