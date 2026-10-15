"""Hero 3: open the link so the family doesn't have to.

daytona:    fresh Daytona sandbox -> runs sandbox_job.py -> Anchor browser -> JSON -> sandbox deleted
quarantine: Anchor browser opens the link (driven from here, no parsing) -> the untrusted bytes go into a fresh
            Daytona sandbox that runs quarantine_job.py -> JSON -> sandbox deleted. Works on Daytona tiers
            that block sandbox egress, because the sandbox needs no network at all.
local:      same job as a local subprocess (fallback when Daytona isn't configured)
mock:       canned result for the Keystone demo page
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
QJOB = Path(__file__).with_name("quarantine_job.py")
SHOTS = Path(__file__).resolve().parent.parent / "data" / "shots"
MOCK_SHOT = Path(__file__).resolve().parent.parent / "mock_sites" / "keystone" / "screenshot.jpg"


async def detonate(url: str, case_id: str) -> dict:
    mode = config.DETONATE_MODE
    if not config.live(config.ANCHOR_API_KEY) or mode == "mock":
        mode = "mock"
    elif mode in ("daytona", "quarantine") and not config.live(config.DAYTONA_API_KEY):
        mode = "local"
    with span("detonate", url=url, mode=mode) as s:
        t0 = time.time()
        if mode in ("daytona", "local", "quarantine"):
            sess = {}
            try:
                try:
                    sess = await _anchor_session()
                    bus.emit("detonation.live", case_id, live_view_url=sess.get("live_view_url"), session=sess.get("id"))
                except Exception as e:
                    if mode != "quarantine":
                        raise
                    # No cloud browser: fetch the bytes without one; they are still parsed only inside the sandbox.
                    bus.emit("detonation.fallback", case_id, browser="http", reason=f"anchor: {str(e)[:120]}")
                fn = {"daytona": _run_daytona, "local": _run_local, "quarantine": _run_quarantine}[mode]
                result = await asyncio.to_thread(fn, url, sess.get("cdp_url"))
            except Exception as e:  # a sponsor outage (e.g. Anchor 402) must never crash a case; the verdict just has less evidence
                result = {"error": f"{type(e).__name__}: {str(e)[:200]}", "final_domain": None}
                bus.emit("detonation.error", case_id, error=result["error"], mode=mode)
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
            sb.process.exec("pip install -q playwright", timeout=120)  # unpinned: the default image is Python 3.14
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


# ---------------- quarantine: fetch here (Anchor), parse in a sandbox with no network ----------------
def _fetch_with_anchor(url: str, cdp_url: str) -> dict:
    """Drive the Anchor cloud browser over CDP. Only observes; returns raw bytes for the sandbox to parse."""
    import urllib.parse
    from playwright.sync_api import sync_playwright

    target = url if url.startswith("http") else "https://" + url
    redirects, out = [], {"download_attempted": False}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("response", lambda r: redirects.append(r.url) if 300 <= r.status < 400 and r.request.is_navigation_request() else None)
        page.on("download", lambda d: out.__setitem__("download_attempted", True) or d.cancel())
        page.goto(target, wait_until="domcontentloaded", timeout=config.DETONATE_TIMEOUT_S * 1000)
        page.wait_for_timeout(1500)
        out.update({
            "final_url": page.url,
            "title": page.title(),
            "html": page.content(),  # untrusted: parsed only inside the sandbox
            "redirects": redirects,
            "shortener": urllib.parse.urlparse(target).hostname in SHORTENERS,
            "screenshot_b64": base64.b64encode(page.screenshot(type="jpeg", quality=60, full_page=False)).decode(),
            "target": target,
        })
        browser.close()
    return out


SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "cutt.ly", "rb.gy", "is.gd", "t.ly")


def _fetch_plain(url: str) -> dict:
    """No browser available: one GET following redirects. No JS runs, nothing is rendered, no screenshot."""
    import re
    import urllib.parse

    target = url if url.startswith("http") else "https://" + url
    with httpx.Client(follow_redirects=True, timeout=config.DETONATE_TIMEOUT_S,
                      headers={"User-Agent": "Mozilla/5.0 Guardian-safe-fetch"}) as c:
        r = c.get(target)
    html = r.text[:2_000_000]
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return {
        "final_url": str(r.url),
        "title": re.sub(r"\s+", " ", m.group(1)).strip() if m else "",
        "html": html,
        "redirects": [str(h.url) for h in r.history],
        "shortener": urllib.parse.urlparse(target).hostname in SHORTENERS,
        "download_attempted": False,
        "target": target,
        "browser": "http",
    }


def _analyze_in_sandbox(fetched: dict) -> dict:
    """The untrusted HTML is parsed inside a throwaway Daytona sandbox that has no network access."""
    from daytona import CreateSandboxFromSnapshotParams, Daytona, DaytonaConfig

    d = Daytona(DaytonaConfig(api_key=config.DAYTONA_API_KEY))
    snap = os.environ.get("DAYTONA_SNAPSHOT", "")
    sb = d.create(CreateSandboxFromSnapshotParams(snapshot=snap)) if snap else d.create()
    t_created = time.time()
    try:
        page = {k: fetched.get(k) for k in ("html", "title", "final_url", "target")}
        sb.fs.upload_file(json.dumps(page, ensure_ascii=False).encode("utf-8"), "/tmp/page.json")
        resp = sb.process.code_run(QJOB.read_text(encoding="utf-8"), timeout=config.DETONATE_TIMEOUT_S + 20)
        out = _parse(resp.result or "")
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


def _domain_age_days(domain: str) -> int | None:
    try:
        r = httpx.get(f"https://rdap.org/domain/{domain}", timeout=6, follow_redirects=True)
        for ev in r.json().get("events", []):
            if ev.get("eventAction") == "registration":
                t = time.strptime(ev["eventDate"][:10], "%Y-%m-%d")
                return int((time.time() - time.mktime(t)) // 86400)
    except Exception:
        return None
    return None


def _run_quarantine(url: str, cdp_url: str | None = None) -> dict:
    fetched = _fetch_with_anchor(url, cdp_url) if cdp_url else _fetch_plain(url)
    fetched.setdefault("browser", "anchor")
    analysed = _analyze_in_sandbox(fetched)
    host = analysed.get("final_domain") or ""
    parts = host.lower().split(".")
    reg = ".".join(parts[-2:]) if len(parts) >= 2 else host
    out = {k: v for k, v in fetched.items() if k != "html"}
    out.update(analysed)
    out["domain_age_days"] = _domain_age_days(reg) if reg else None
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
