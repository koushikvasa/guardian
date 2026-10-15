"""The help voice note as a page anyone can open from a text: title, three steps, audio, share button.
Served by the backend (GET /help/{case_id}) so it works through the public tunnel on any phone."""
import html
import json

UI = {
    "en": {"from": "A story from {name}", "listen": "Listen (20 seconds)", "share": "Share with a friend",
           "foot": "Guardian is a family scam shield. It never asks for codes, passwords or money."},
    "es": {"from": "Una historia de {name}", "listen": "Escuchar (20 segundos)", "share": "Compartir con una amiga",
           "foot": "Guardian es un escudo familiar contra estafas. Nunca pide códigos, contraseñas ni dinero."},
    "te": {"from": "{name} చెప్పిన కథ", "listen": "వినండి (20 సెకన్లు)", "share": "స్నేహితులకు పంపండి",
           "foot": "Guardian కుటుంబాల కోసం మోసాల నుంచి రక్షణ. ఇది ఎప్పుడూ కోడ్‌లు, పాస్‌వర్డ్‌లు, డబ్బు అడగదు."},
}


def render(case: dict, name: str, title: str, steps: list[str], audio_url: str | None, lang: str) -> str:
    ui = UI.get(lang, UI["en"])
    e = html.escape
    audio = (f'<audio controls preload="none" src="{e(audio_url)}" style="width:100%;margin:18px 0 6px"></audio>'
             f'<div class="muted">{e(ui["listen"])}</div>') if audio_url else ""
    share_text = json.dumps(f"{title}\n\n" + "\n".join(f"• {s}" for s in steps), ensure_ascii=False)
    items = "".join(f'<li>{e(s)}</li>' for s in steps)
    return f"""<!doctype html>
<html lang="{e(lang)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>{e(title)}</title>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;600;700&family=Young+Serif&display=swap" rel="stylesheet">
<style>
:root{{--bg:#EEF1F6;--ink:#161B33;--accent:#2E46E5;--muted:#4A5170;--card:#fff;--line:#D9DEE9}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:Figtree,system-ui,sans-serif;font-size:19px;line-height:1.45}}
main{{max-width:520px;margin:0 auto;padding:28px 18px 48px}}
.brand{{display:flex;align-items:center;gap:10px;font-weight:700;color:var(--accent)}}
.brand i{{display:inline-block;width:28px;height:28px;border-radius:50%;background:var(--accent)}}
h1{{font-family:'Young Serif',Georgia,serif;font-weight:400;font-size:34px;line-height:1.12;margin:22px 0 6px}}
.muted{{color:var(--muted);font-size:15px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px 20px;margin-top:18px}}
ol{{margin:0;padding-left:26px}} li{{margin:10px 0}}
button{{width:100%;min-height:56px;margin-top:18px;border:0;border-radius:14px;background:var(--ink);color:#fff;font:inherit;font-weight:700;font-size:18px}}
footer{{margin-top:28px;color:var(--muted);font-size:14px;text-align:center}}
</style></head><body><main>
<div class="brand"><i></i> Guardian</div>
<h1>{e(title)}</h1>
<div class="muted">{e(ui["from"].format(name=name))}</div>
<div class="card"><ol>{items}</ol>{audio}</div>
<button id="share">{e(ui["share"])}</button>
<footer>{e(ui["foot"])}</footer>
<script>
const text={share_text};
document.getElementById('share').onclick=async()=>{{
  if(navigator.share){{try{{await navigator.share({{title:document.title,text,url:location.href}});return}}catch(e){{}}}}
  location.href='https://wa.me/?text='+encodeURIComponent(text+'\\n'+location.href);
}};
</script></main></body></html>"""
