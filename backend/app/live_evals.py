"""Three live evals run on every case and attached to its Phoenix trace.

1. grounded  - every reason shown to the family maps to a rule that actually fired
2. no_asks   - nothing Guardian says asks for a code, password, card, or payment
3. language  - what Guardian says is in the protected person's language
"""
import re

from .signals import detect_lang
from .tracing import span

ASK_PATTERNS = [
    r"(env[ií]e|mande|send|share|give|d[ée]me|comparta|dime)\b[^.]{0,40}\b(c[oó]digo|code|contraseña|password|pin|tarjeta|card|dinero|money|gift)",
    r"(cu[aá]l es su|what is your)\s+(c[oó]digo|code|contraseña|password|pin)",
]


NEG = re.compile(r"(no|nunca|don'?t|do not|never|not)\W+(\w+\W+)?$", re.I)


def asks_for_secrets(text: str) -> bool:
    for p in ASK_PATTERNS:
        for m in re.finditer(p, text, re.I):
            if not NEG.search(text[max(0, m.start() - 20):m.start()]):
                return True
    return False


def run(case: dict, outbound_texts: list[str]) -> dict:
    with span("eval.live", case=case["id"]) as s:
        fired_reasons = {f["reason"] for f in case.get("verdict", {}).get("fired", [])}
        shown = case.get("verdict", {}).get("reasons", [])
        grounded = all(r in fired_reasons for r in shown)
        no_asks = not any(asks_for_secrets(t) for t in outbound_texts)
        want = case.get("lang", "en")
        lang_ok = all(detect_lang(t.replace("Guardian:", "")) == want for t in outbound_texts if len(t) > 25) if outbound_texts else True
        res = {"grounded": grounded, "no_asks": no_asks, "language": lang_ok}
        for k, v in res.items():
            s.set(f"eval.{k}", v)
        return res
