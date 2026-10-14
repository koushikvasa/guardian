"""ElevenLabs Agents + Twilio outbound calls.

Live: POST /v1/convai/twilio/outbound-call, then poll GET /v1/convai/conversations/{id}.
      Status goes initiated -> in-progress -> processing -> done; the transcript and the data-collection
      results only appear at "done" (verified 2026-10-14), so captions arrive together at the end.
      The post-call webhook (/webhooks/elevenlabs) resolves the call faster when configured.
Mock: a scripted transcript is played as events, outcome from MOCK_* settings.
"""
import asyncio
import re
import time

import httpx

from . import bus, config
from .tracing import span

API = "https://api.elevenlabs.io/v1/convai"
_TAGS = re.compile(r"\[(?:slow|warm|happy|calm|sad|excited|whisper|laughs?|sighs?|pause|[a-z ]{1,20})\]\s*")


def caption(text: str) -> str:
    """Transcript lines carry v4 delivery tags like [slow] [warm]; they aren't spoken, so keep them off the screen."""
    return _TAGS.sub("", text or "").strip()
_waiters: dict[str, asyncio.Future] = {}  # conversation_id -> future(result)


def _live() -> bool:
    return config.live(config.ELEVENLABS_API_KEY, config.ELEVENLABS_PHONE_NUMBER_ID)


async def place_call(kind: str, case_id: str, to_phone: str, agent_id: str, variables: dict,
                     mock_script: list[tuple[str, str]], mock_result: dict, max_wait_s: int = 180) -> dict:
    """Returns {"status": "completed"|"no_answer"|"failed", "data": {...}, "transcript": [...]}"""
    with span(f"call.{kind}", to=to_phone[-4:], agent=agent_id or "mock") as s:
        bus.emit(f"call.{kind}.dialing", case_id, to=to_phone)
        if not (_live() and agent_id):
            res = await _mock_call(kind, case_id, mock_script, mock_result)
        else:
            res = await _live_call(kind, case_id, to_phone, agent_id, variables, max_wait_s)
        bus.emit(f"call.{kind}.ended", case_id, status=res["status"], data=res.get("data", {}))
        s.set("status", res["status"])
        s.set("data", str(res.get("data")))
        return res


async def _mock_call(kind, case_id, script, result):
    await asyncio.sleep(1.5 * config.MOCK_CALL_SPEED)
    if result.get("status") == "no_answer":
        await asyncio.sleep(2 * config.MOCK_CALL_SPEED)
        return {"status": "no_answer", "data": {}, "transcript": []}
    bus.emit(f"call.{kind}.connected", case_id)
    transcript = []
    for role, text in script:
        await asyncio.sleep(max(0.6, len(text) / 28) * config.MOCK_CALL_SPEED)
        transcript.append({"role": role, "message": text})
        bus.emit(f"call.{kind}.transcript", case_id, role=role, text=text)
    return {"status": "completed", "data": result.get("data", {}), "transcript": transcript}


async def _live_call(kind, case_id, to_phone, agent_id, variables, max_wait_s):
    headers = {"xi-api-key": config.ELEVENLABS_API_KEY}
    body = {
        "agent_id": agent_id,
        "agent_phone_number_id": config.ELEVENLABS_PHONE_NUMBER_ID,
        "to_number": to_phone,
        "conversation_initiation_client_data": {"dynamic_variables": {k: str(v) for k, v in variables.items()}},
    }
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{API}/twilio/outbound-call", json=body, headers=headers)
        if r.status_code >= 300:
            bus.emit(f"call.{kind}.error", case_id, error=r.text[:300])
            return {"status": "failed", "data": {}, "transcript": []}
        conv_id = r.json().get("conversation_id")
        bus.emit(f"call.{kind}.placed", case_id, conversation_id=conv_id)

        fut = asyncio.get_running_loop().create_future()
        _waiters[conv_id] = fut
        seen, connected, t0 = 0, False, time.time()
        try:
            while time.time() - t0 < max_wait_s:
                if fut.done():
                    return fut.result()
                await asyncio.sleep(1.5)
                g = await c.get(f"{API}/conversations/{conv_id}", headers=headers)
                if g.status_code >= 300:
                    continue
                conv = g.json()
                tr = conv.get("transcript") or []
                status = conv.get("status")
                # ElevenLabs only exposes the transcript once the call is done ("processing" -> "done"),
                # so "connected" comes from the status, and the captions arrive together at the end.
                if (status in ("in-progress", "processing") or tr) and not connected:
                    connected = True
                    bus.emit(f"call.{kind}.connected", case_id)
                for line in tr[seen:]:
                    if caption(line.get("message")):
                        bus.emit(f"call.{kind}.transcript", case_id, role=line.get("role"), text=caption(line["message"]))
                seen = len(tr)
                if status in ("done", "failed"):
                    return _result_from_conversation(conv, connected)
            return {"status": "no_answer", "data": {}, "transcript": []}
        finally:
            _waiters.pop(conv_id, None)


def _result_from_conversation(conv: dict, connected: bool) -> dict:
    analysis = conv.get("analysis") or {}
    dc = analysis.get("data_collection_results") or {}
    data = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in dc.items()}
    tr = [{**t, "message": caption(t.get("message"))} for t in (conv.get("transcript") or [])]
    user_spoke = any(t.get("role") == "user" and t.get("message") for t in tr)
    if conv.get("status") == "failed" or not (connected and user_spoke):
        return {"status": "no_answer", "data": data, "transcript": tr}
    return {"status": "completed", "data": data, "transcript": tr}


def resolve_from_webhook(payload: dict):
    """Called by /webhooks/elevenlabs (post_call_transcription or call_initiation_failure)."""
    data = payload.get("data") or {}
    conv_id = data.get("conversation_id")
    fut = _waiters.get(conv_id)
    if not fut or fut.done():
        return
    if payload.get("type") == "call_initiation_failure":
        fut.set_result({"status": "no_answer", "data": {}, "transcript": []})
    else:
        fut.set_result(_result_from_conversation({**data, "status": "done"}, connected=True))
