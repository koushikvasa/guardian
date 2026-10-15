"""Daniel's second key as a page served by the backend, so the link in his text opens on his phone through the
public tunnel. Same rules as the Next.js page: "Don't send it" is one tap; approval is a 1.5 s press-and-hold;
Guardian never approves on its own."""
import html
import json

LANG_NAME = {"en": "English", "es": "Spanish", "te": "Telugu"}


def render(case: dict, api_base: str) -> str:
    e = html.escape
    money = case.get("money") or {}
    who = {"jasmine": "Jasmine", "amma": "Amma", "rosa": "Rosa"}.get(case.get("protected"), case.get("protected") or "Mom").title()
    in_lang = LANG_NAME.get(case.get("lang") or "en", "English")
    reasons = [f.get("reason_en") or f.get("reason") for f in (case.get("verdict") or {}).get("fired", []) if f.get("weight", 0) > 0]
    mem = [(h.get("when") or "", h.get("text") or "") for h in (case.get("memory") or {}).get("hits", [])[:2]]
    amount = f"{int(money.get('amount') or 0):,}"
    state = money.get("state") or "none"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Guardian key · {e(case['id'])}</title>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;600;700&family=Young+Serif&display=swap" rel="stylesheet">
<style>
:root{{--bg:#EEF1F6;--ink:#161B33;--accent:#2E46E5;--danger:#D7322A;--gold:#B8862B;--ok:#14705A;--muted:#4A5170;--card:#fff;--line:#D9DEE9}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:Figtree,system-ui,sans-serif;font-size:17px;line-height:1.4}}
main{{max-width:420px;min-height:100vh;margin:0 auto;padding:28px 22px;display:flex;flex-direction:column}}
.brand{{display:flex;align-items:center;gap:10px;font-weight:700;color:var(--accent)}} .brand i{{display:inline-block;width:26px;height:26px;border-radius:50%;background:var(--accent)}}
.muted{{color:var(--muted)}} h1{{font-family:'Young Serif',Georgia,serif;font-weight:400;font-size:34px;line-height:1.12;margin:8px 0 0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:14px 16px;margin-top:14px}}
.btn{{width:100%;min-height:58px;border:0;border-radius:14px;font:inherit;font-weight:700;font-size:19px;touch-action:none;user-select:none;-webkit-user-select:none}}
.dark{{background:var(--ink);color:#fff}} .hold{{margin-top:12px;background:#fff;border:2px solid var(--gold);color:#6B4A10;position:relative;overflow:hidden}}
.hold span{{position:absolute;inset:0;width:0;background:#F6E7C5;z-index:0}} .hold b{{position:relative;z-index:1}}
.done{{margin-top:auto;padding-top:24px;text-align:center;font-weight:700;font-size:20px}}
</style></head><body><main>
<div class="brand"><i></i> Guardian</div>
{"<p class='muted' style='margin-top:40px;font-size:18px'>No money request is waiting for your key.</p>" if not money else f'''
<div class="muted" style="margin-top:26px">{e(who)} needs your key</div>
<h1>{e(who)} wants to send ${amount}</h1>
<div style="margin-top:18px;font-weight:700">What Guardian found</div>
{"".join(f'<div style="margin-top:8px">• {e(r)}</div>' for r in reasons)}
{f'<div class="card"><div style="font-weight:700;font-size:14px;margin-bottom:6px">Guardian remembers</div>' + "".join(f'<div style="font-size:14px;margin-top:4px"><span class="muted">{e(w)} · </span>{e(t)}</div>' for w, t in mem) + '</div>' if mem else ''}
<div id="actions" style="margin-top:auto;padding-top:24px">
  <button class="btn dark" id="decline">Don’t send it</button>
  <button class="btn hold" id="hold"><span id="fill"></span><b>Press and hold to approve</b></button>
  <div class="muted" style="font-size:14px;text-align:center;margin-top:12px">Guardian tells {e(who)} your answer in {e(in_lang)}.</div>
</div>
<div id="result" class="done" hidden></div>
'''}
<script>
const API={json.dumps(api_base)}, ID={json.dumps(case['id'])}, WHO={json.dumps(who)}, LANG={json.dumps(in_lang)};
let state={json.dumps(state)};
function show(s){{
  state=s; if(s==='locked'||s==='none')return;
  document.getElementById('actions').hidden=true; const r=document.getElementById('result'); r.hidden=false;
  r.style.color = s==='declined' ? 'var(--danger)' : 'var(--ok)';
  r.textContent = s==='declined' ? `Stopped. Guardian is telling ${{WHO}} in ${{LANG}}.` : `Approved. Guardian told ${{WHO}}.`;
}}
async function turn(d){{ await fetch(`${{API}}/cases/${{ID}}/key`,{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{decision:d}})}}); show(d==='decline'?'declined':'approved'); }}
if(state!=='none'){{
  show(state);
  document.getElementById('decline').onclick=()=>turn('decline');
  const hold=document.getElementById('hold'), fill=document.getElementById('fill'); let t0=null, raf=null;
  const stop=()=>{{ t0=null; if(raf)cancelAnimationFrame(raf); fill.style.width='0'; }};
  const tick=()=>{{ if(t0===null)return; const p=Math.min(1,(Date.now()-t0)/1500); fill.style.width=(p*100)+'%'; if(p>=1){{stop(); turn('approve'); return;}} raf=requestAnimationFrame(tick); }};
  hold.addEventListener('pointerdown',ev=>{{ev.preventDefault(); hold.setPointerCapture(ev.pointerId); t0=Date.now(); tick();}});
  ['pointerup','pointercancel','pointerleave'].forEach(n=>hold.addEventListener(n,stop));
  setInterval(async()=>{{ if(state!=='locked')return; try{{const c=await (await fetch(`${{API}}/cases/${{ID}}`)).json(); if(c.money&&c.money.state!=='locked')show(c.money.state);}}catch(e){{}} }},2000);
}}
</script></main></body></html>"""
