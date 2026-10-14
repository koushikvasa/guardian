"""Twilio SMS out. Mock mode only emits the event (the Rosa phone screen shows it either way)."""
import asyncio

import httpx

from . import bus, config


async def send(case_id: str | None, to: str, body: str, role: str = "protected"):
    bus.emit("sms.out", case_id, to=to, body=body, role=role)
    if not config.live(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN, config.TWILIO_FROM):
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}/Messages.json"
    try:
        await asyncio.to_thread(
            httpx.post, url, data={"To": to, "From": config.TWILIO_FROM, "Body": body},
            auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN), timeout=10,
        )
    except Exception as e:
        bus.emit("sms.error", case_id, error=str(e))
