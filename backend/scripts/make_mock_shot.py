"""Render mock_sites/keystone to screenshot.jpg (used by mock detonation)."""
from pathlib import Path
from playwright.sync_api import sync_playwright
root = Path(__file__).resolve().parent.parent / "mock_sites" / "keystone"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 520, "height": 620})
    pg.goto((root / "index.html").as_uri()); pg.screenshot(path=str(root / "screenshot.jpg"), type="jpeg", quality=70); b.close()
print("wrote", root / "screenshot.jpg")
