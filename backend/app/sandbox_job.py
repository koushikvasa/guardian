"""Runs INSIDE the Daytona sandbox (or locally in DETONATE_MODE=local).

Self-contained on purpose: Daytona receives this file's source and executes it.
It opens the link in an Anchor cloud browser, observes, and prints ONE JSON line.
It never types into fields, never submits, never downloads.

Inputs come from env: TARGET_URL, ANCHOR_API_KEY, TIMEOUT_S.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

OFFICIAL = {
    "Keystone Bank": ["keystonebank.com"],
    "Chase": ["chase.com"],
    "Bank of America": ["bankofamerica.com"],
    "Wells Fargo": ["wellsfargo.com"],
    "USPS": ["usps.com"],
    "Amazon": ["amazon.com"],
    "PayPal": ["paypal.com"],
    "IRS": ["irs.gov"],
}
SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "cutt.ly", "rb.gy", "is.gd", "t.ly")


def _http_json(url, method="GET", headers=None, body=None, timeout=10):
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=json.dumps(body).encode() if body is not None else None)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def registrable(host):
    parts = host.lower().split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def domain_age_days(domain):
    try:
        data = _http_json(f"https://rdap.org/domain/{domain}", timeout=6)
        for ev in data.get("events", []):
            if ev.get("eventAction") == "registration":
                t = time.strptime(ev["eventDate"][:10], "%Y-%m-%d")
                return int((time.time() - time.mktime(t)) // 86400)
    except Exception:
        return None
    return None


def main():
    target = os.environ["TARGET_URL"]
    if not target.startswith("http"):
        target = "https://" + target
    timeout_s = int(os.environ.get("TIMEOUT_S", "20"))
    started = time.time()
    # Preferred: Guardian opens the Anchor session and hands over only its CDP URL,
    # so the sandbox never holds the Anchor API key.
    cdp_url = os.environ.get("CDP_URL")
    key = os.environ.get("ANCHOR_API_KEY", "")
    session_id = None
    if not cdp_url:
        sess = _http_json("https://api.anchorbrowser.io/v1/sessions", "POST", {"anchor-api-key": key}, {})
        sess = sess.get("data", sess)
        session_id, cdp_url = sess["id"], sess["cdp_url"]

    redirects, out = [], {}
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url)
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.on("response", lambda r: redirects.append(r.url) if 300 <= r.status < 400 and r.request.is_navigation_request() else None)
            page.on("download", lambda d: out.__setitem__("download_attempted", True) or d.cancel())
            page.goto(target, wait_until="domcontentloaded", timeout=timeout_s * 1000)
            page.wait_for_timeout(1500)
            final_url = page.url
            title = page.title()
            text = page.inner_text("body")[:4000] if page.query_selector("body") else ""
            fields = page.eval_on_selector_all(
                "input, select, textarea",
                "els => els.filter(e => e.type !== 'hidden').map(e => (e.labels && e.labels[0] ? e.labels[0].innerText : '') || e.placeholder || e.name || e.type)",
            )
            shot = page.screenshot(type="jpeg", quality=60, full_page=False)
            browser.close()
    finally:
        if session_id:
            try:
                _http_json(f"https://api.anchorbrowser.io/v1/sessions/{session_id}", "DELETE", {"anchor-api-key": key})
            except Exception:
                pass

    host = urllib.parse.urlparse(final_url).hostname or ""
    reg = registrable(host)
    hay = (title + " " + text).lower()
    brands = [b for b in OFFICIAL if b.lower().split()[0] in hay]
    official = bool(brands) and any(reg == d or host.endswith("." + d) for b in brands for d in OFFICIAL[b])
    import base64

    out.update({
        "final_url": final_url,
        "final_domain": host,
        "redirects": redirects,
        "shortener": urllib.parse.urlparse(target).hostname in SHORTENERS,
        "title": title,
        "brands": brands,
        "official_domain": official,
        "form_fields": [f.strip() for f in fields if f and f.strip()][:12],
        "domain_age_days": domain_age_days(reg),
        "screenshot_b64": base64.b64encode(shot).decode(),
        "download_attempted": out.get("download_attempted", False),
        "anchor_session": session_id,
        "elapsed_s": round(time.time() - started, 2),
    })
    print("GUARDIAN_RESULT " + json.dumps(out))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("GUARDIAN_RESULT " + json.dumps({"error": f"{type(e).__name__}: {e}"}))
        sys.exit(0)
