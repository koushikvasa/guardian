"""Remove personal data before any text leaves for an LLM or a trace."""
import re

_PATTERNS = [
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[CARD]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    # one-time codes: 4-8 digits next to code words
    (re.compile(r"(?i)(c[oó]digo|code|otp|pin|clave)\D{0,12}(\d{4,8})"), r"\1 [CODE]"),
]


def scrub(text: str) -> str:
    out = text
    for pat, rep in _PATTERNS:
        out = pat.sub(rep, out)
    return out
