"""Runs INSIDE a Daytona sandbox in DETONATE_MODE=quarantine (stdlib only, no network needed).

Guardian fetched the page through an Anchor cloud browser and wrote the untrusted bytes to /tmp/page.json:
  {"html": ..., "title": ..., "final_url": ..., "target": ...}
This file parses them (forms, brands, scripts, frames, download links) and prints ONE JSON line.
Nothing from the page is ever parsed on the family's machine or on Guardian's host.
"""
import json
import os
import re
import sys
import urllib.parse
from html.parser import HTMLParser

OFFICIAL = {
    "Keystone Bank": ["keystonebank.com"],
    "Chase": ["chase.com"],
    "Bank of America": ["bankofamerica.com"],
    "Wells Fargo": ["wellsfargo.com"],
    "USPS": ["usps.com"],
    "Amazon": ["amazon.com"],
    "PayPal": ["paypal.com"],
    "IRS": ["irs.gov"],
    "Netflix": ["netflix.com"],
}
DOWNLOAD_EXT = (".exe", ".apk", ".zip", ".scr", ".msi", ".dmg", ".bat", ".js", ".vbs")
GENERIC = {"bank", "banco"}  # never treat a generic word as a brand match


class _P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields, self.labels, self.text, self.scripts, self.iframes, self.links = [], {}, [], [], [], []
        self._label_for, self._in_label, self._skip = None, False, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("input", "select", "textarea"):
            if (a.get("type") or "").lower() != "hidden":
                self.fields.append({"id": a.get("id"), "placeholder": a.get("placeholder"), "name": a.get("name"), "type": a.get("type") or tag})
        elif tag == "label":
            self._in_label, self._label_for = True, a.get("for")
            self.labels.setdefault(a.get("for"), "")
        elif tag == "script":
            self._skip += 1
            if a.get("src"):
                self.scripts.append(a["src"])
        elif tag == "style":
            self._skip += 1
        elif tag == "iframe":
            st = (a.get("style") or "").replace(" ", "").lower()
            hidden = "display:none" in st or "visibility:hidden" in st or a.get("width") in ("0", "1") or a.get("height") in ("0", "1")
            self.iframes.append({"src": a.get("src"), "hidden": hidden})
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "label":
            self._in_label = False
        elif tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._skip:
            return
        d = data.strip()
        if not d:
            return
        if self._in_label:
            self.labels[self._label_for] = (self.labels.get(self._label_for, "") + " " + d).strip()
        self.text.append(d)


def analyze(page: dict) -> dict:
    p = _P()
    p.feed(page.get("html") or "")
    title = page.get("title") or ""
    final_url = page.get("final_url") or ""
    host = urllib.parse.urlparse(final_url).hostname or ""
    parts = host.lower().split(".")
    reg = ".".join(parts[-2:]) if len(parts) >= 2 else host
    text = " ".join(p.text)[:4000]
    hay = (title + " " + text).lower()
    brands = [b for b in OFFICIAL if b.lower() in hay or (b.lower().split()[0] not in GENERIC and b.lower().split()[0] in hay)]
    official = bool(brands) and any(reg == d or host.endswith("." + d) for b in brands for d in OFFICIAL[b])
    fields = []
    for f in p.fields:
        label = p.labels.get(f["id"]) if f["id"] else None
        fields.append((label or f["placeholder"] or f["name"] or f["type"] or "").strip())
    scripts_ext = [s for s in p.scripts if urllib.parse.urlparse(urllib.parse.urljoin(final_url, s)).hostname not in (host, None)]
    downloads = [l for l in p.links if l.lower().split("?")[0].endswith(DOWNLOAD_EXT)]
    return {
        "final_domain": host,
        "title": title,
        "brands": brands,
        "official_domain": official,
        "form_fields": [f for f in fields if f][:12],
        "asks_credentials": any(any(k in f.lower() for k in ("pass", "contraseña", "contrasena", "card", "tarjeta", "cvv", "ssn", "pin", "código", "codigo", "otp")) for f in fields),
        "external_scripts": len(scripts_ext),
        "hidden_iframes": sum(1 for i in p.iframes if i["hidden"]),
        "download_links": downloads[:5],
        "text_excerpt": text[:300],
        "html_bytes": len(page.get("html") or ""),
    }


if __name__ == "__main__":
    try:
        src = os.environ.get("PAGE_JSON", "/tmp/page.json")
        with open(src, encoding="utf-8") as f:
            page = json.load(f)
        print("GUARDIAN_RESULT " + json.dumps(analyze(page), ensure_ascii=False))
    except Exception as e:
        print("GUARDIAN_RESULT " + json.dumps({"error": f"{type(e).__name__}: {e}"}))
        sys.exit(0)
