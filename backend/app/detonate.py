"""Hero 3: open the link so the family doesn't have to.

daytona: fresh Daytona sandbox -> runs sandbox_job.py -> Anchor browser -> JSON -> sandbox deleted
local:   same job as a local subprocess (fallback if the Daytona tier blocks outbound network)
mock:    canned result for the Keystone demo page
"""
import asyncio
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

from . import bus, config
from .tracing import span

JOB = Path(__file__).with_name("sandbox_job.py")
SHOTS = Path(__file__).resolve().parent.parent / "data" / "shots"
MOCK_SHOT = Path(__file__).resolve().parent.parent / "mock_sites" / "keystone" / "screenshot.jpg"


async def detonate(url: str, case_id: str) -> dict:
    mode = config.DETONATE_MODE
    if not config.live(config.ANCHOR_API_KEY) or mode == "mock":
        mode = "mock"
    elif mode == "daytona" and not config.live(config.DAYTONA_API_KEY):
        mode = "local"
    with span("detonate", url=url, mode=mode) as s:
        t0 = time.time()
        if mode in ("daytona", "local"):
            sess = await _anchor_session()
            bus.emit("detonation.live", case_id, live_view_url=sess.get("live_view_url"), session=sess.get("id"))
            try:
                fn = _run_daytona if mode == "daytona" else _run_local
                result = await asyncio.to_thread(fn, url, sess.get("cdp_url"))
            finally:
                await _anchor_close(sess.get("id"))
            result["anchor_session"] = sess.get("id")
        else:
            await asyncio.sleep(2.0)
            result = _mock(url)
        result["mode"] = mode
        result["elapsed_s"] = round(time.time() - t0, 2)
        shot = result.pop("screenshot_b64", None)
        if shot:
            SHOTS.mkdir(parents=True, exist_ok=True)
            (SHOTS / f"{case_id}.jpg").write_bytes(base64.b64decode(shot))
            result["screenshot_url"] = f"/shots/{case_id}.jpg"
        s.set("result", json.dumps({k: v for k, v in result.items()}, ensure_ascii=False)[:2000])
        return result


ANCHOR = "https://api.anchorbrowser.io/v1/sessions"


async def _anchor_session() -> dict:
    """Guardian opens the cloud browser; the sandbox only gets its CDP URL (never the API key)."""
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(ANCHOR, headers={"anchor-api-key": config.ANCHOR_API_KEY}, json={})
        r.raise_for_status()
        d = r.json()
        return d.get("data", d)  # id, cdp_url, live_view_url (shown live on the Jar screen)


async def _anchor_close(session_id):
    if not session_id:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.delete(f"{ANCHOR}/{session_id}", headers={"anchor-api-key": config.ANCHOR_API_KEY})
    except Exception:
        pass


def _parse(stdout: str) -> dict:
    for line in reversed(stdout.splitlines()):
        if line.startswith("GUARDIAN_RESULT "):
            return json.loads(line[len("GUARDIAN_RESULT "):])
    return {"error": "no result", "raw": stdout[-500:]}


def _run_local(url: str, cdp_url: str | None = None) -> dict:
    env = {**os.environ, "TARGET_URL": url, "CDP_URL": cdp_url or "", "TIMEOUT_S": str(config.DETONATE_TIMEOUT_S)}
    if not cdp_url:
        env["ANCHOR_API_KEY"] = config.ANCHOR_API_KEY
    p = subprocess.run([sys.executable, "-I", str(JOB)], env=env, capture_output=True, text=True, timeout=config.DETONATE_TIMEOUT_S + 30)
    return _parse(p.stdout)


def _run_daytona(url: str, cdp_url: str | None = None) -> dict:
    from daytona import Daytona, DaytonaConfig

    d = Daytona(DaytonaConfig(api_key=config.DAYTONA_API_KEY))
    snap = os.environ.get("DAYTONA_SNAPSHOT", "")
    if snap:  # pre-built image with Playwright: ~1-3 s start instead of a 30 s pip install
        from daytona import CreateSandboxFromSnapshotParams
        sb = d.create(CreateSandboxFromSnapshotParams(snapshot=snap))
    else:
        sb = d.create()
    t_created = time.time()
    try:
        if not snap:
            sb.process.exec("pip install -q playwright==1.48.0", timeout=120)
        code = (
            "import os\n"
            f"os.environ['TARGET_URL'] = {url!r}\n"
            f"os.environ['CDP_URL'] = {(cdp_url or '')!r}\n"
            f"os.environ['TIMEOUT_S'] = '{config.DETONATE_TIMEOUT_S}'\n"
            + JOB.read_text(encoding="utf-8")
        )
        resp = sb.process.code_run(code, timeout=config.DETONATE_TIMEOUT_S + 20)
        out = _parse(resp.result)
    finally:
        t_del = time.time()
        try:
            d.delete(sb)
        except AttributeError:
            sb.delete()
        out_del = round(time.time() - t_del, 2)
    out["sandbox_id"] = getattr(sb, "id", "")
    out["sandbox_destroyed_s"] = out_del
    out["sandbox_lifetime_s"] = round(time.time() - t_created, 2)
    return out


def _mock(url: str) -> dict:
    shot = base64.b64encode(MOCK_SHOT.read_bytes()).decode() if MOCK_SHOT.exists() else None
    return {
        "final_url": "https://keystone-verifica.top/login",
        "final_domain": "keystone-verifica.top",
        "redirects": ["https://bit.ly/kst-verif", "https://t.ly/r/9f2", "https://go.keystone-verifica.top/a"],
        "shortener": True,
        "title": "Keystone Bank | Verifique su cuenta",
        "brands": ["Keystone Bank"],
        "official_domain": False,
        "form_fields": ["Usuario", "Contraseña", "Número de tarjeta y CVV"],
        "domain_age_days": 3,
        "download_attempted": False,
        "sandbox_id": "mock-sbx-a2041",
        "sandbox_destroyed_s": 0.8,
        **({"screenshot_b64": shot} if shot else {}),
    }
