"""Signal extraction. Bedrock (Claude) returns JSON; a regex extractor is the mock twin and the fallback.

The LLM never sees un-scrubbed text and never produces the verdict.
"""
import json
import re

from . import config
from .tracing import span

URL_RE = re.compile(r"(https?://\S+|\b(?:bit\.ly|tinyurl\.com|t\.co|cutt\.ly|rb\.gy|is\.gd|t\.ly)/\S+|\b[a-z0-9-]+\.(?:top|xyz|click|info|online|site|live|shop)(?:/\S*)?)", re.I)
SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "cutt.ly", "rb.gy", "is.gd", "t.ly")

# Telugu alternatives sit outside the \b groups: \b is unreliable around Telugu vowel signs.
FAMILY_WORDS = r"(?:\b(soy tu hij[oa]|soy (daniel|tu nieto|tu nieta)|mam[aá]|abuel[ao]|it'?s me,? (mom|grandma|grandpa)|mom,? it'?s|grandma,? it'?s|soy yo)\b|అమ్మా|అమ్మ |నానమ్మ|అమ్మమ్మ|నేను (?:[A-Z][a-z]+))"
SECRECY = r"(?:\b(no le digas|no le diga|no se lo digas|secreto|don'?t tell|keep (this|it) (between us|secret|quiet))\b|ఎవరికీ చెప్పొద్దు|ఎవ్వరికీ చెప్ప|రహస్యం)"
URGENCY = r"(?:\b(ya mismo|ahora mismo|urgente|en 24 horas|inmediatamente|hoy mismo|right now|urgent|immediately|within 24 hours|asap|final notice)\b|వెంటనే|అర్జెంట్|ఇప్పుడే|24 గంటల్లో|ఈ రోజే)"
MONEY = r"(\$\s?[\d,]+|\b\d[\d,]*\s?(d[oó]lares|dollars|usd)\b)"
METHODS = {
    "gift_card": r"gift ?cards?|tarjetas? de regalo|google play|itunes|steam card|గిఫ్ట్ కార్డ",
    "wire": r"\bwire\b|transferencia|giro|వైర్",
    "crypto": r"crypto|bitcoin|usdt|cripto",
    "zelle": r"zelle",
    "western_union": r"western union",
    "cash_courier": r"mensajero|courier|recoger el efectivo|pick up the cash",
    "bitcoin_atm": r"bitcoin atm|cajero de bitcoin",
}
REMOTE_ACCESS = r"(?:\b(anydesk|teamviewer|ultraviewer|logmein|quick ?assist|remote (?:access|control|desktop)|access (?:to )?(?:my|your) (?:computer|pc|laptop|phone)|share (?:my|your) screen|install (?:this|an?) (?:app|program|software)|acceso remoto|controlar (?:mi|su) computadora|instale (?:esta|una) aplicaci[oó]n)\b|రిమోట్|ఇన్‌స్టాల్ చేయ|స్క్రీన్ షేర్)"
TECH_SUPPORT = r"(?:\b(virus|infected|hacked|malware|security alert|license (?:has )?expired|tech(?:nical)? support|refund department|refund of \$?[\d,]+|overcharged|your (?:computer|pc|laptop) (?:has been|is) (?:compromised|infected|locked)|do not turn off|soporte t[eé]cnico|tiene un virus|reembolso)\b|వైరస్|హ్యాక్|కంప్యూటర్‌లో సమస్య|రీఫండ్)"
CALLBACK_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\b[2-9]\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
BRANDS = {
    "Microsoft": r"microsoft|windows (?:defender|security|support)",
    "Apple": r"apple (?:support|security|id)|icloud",
    "Norton": r"\bnorton\b|mcafee|geek squad",
    "Social Security": r"social security|\bssa\b|medicare",
    "Keystone Bank": r"keystone",
    "Chase": r"\bchase\b",
    "Bank of America": r"bank of america|bofa",
    "Wells Fargo": r"wells fargo",
    "USPS": r"\busps\b|correo postal",
    "Amazon": r"amazon",
    "PayPal": r"paypal",
    "IRS": r"\birs\b",
}
NAME_RE = re.compile(r"soy (daniel|[A-Z][a-z]+)|it'?s me,? ([A-Z][a-z]+)|నేను ([A-Z][a-z]+)", re.I)

PROMPT = """You extract scam signals from one message a family member received. Return ONLY JSON:
{"urls": [string], "claims_family": bool, "claimed_name": string|null,
 "money_request": {"amount": number|null, "method": "gift_card"|"wire"|"crypto"|"zelle"|"western_union"|"cash_courier"|"bitcoin_atm"|"other"} | null,
 "secrecy": bool, "urgency": bool, "brand": string|null, "shortener": bool, "language": "es"|"en"|"te",
 "remote_access": bool, "tech_support_claim": bool, "callback_number": string|null}
remote_access = they want software installed or access to the device; tech_support_claim = an unsolicited "virus /
security / refund / support" story from a company or agency; callback_number = a phone number to call back.
Do not judge whether it is a scam. Only report what is in the text.
Message:
"""


def extract(text: str) -> dict:
    with span("signals.extract", mode="bedrock" if config.live(config.BEDROCK_MODEL_ID) else "regex") as s:
        out = None
        if config.live(config.BEDROCK_MODEL_ID):
            try:
                out = _bedrock(text)
            except Exception as e:  # never block a case on the LLM
                s.set("error", str(e))
        if out is None:
            out = regex_extract(text)
        # always union URLs found by regex, the LLM sometimes drops them
        out["urls"] = sorted(set(out.get("urls") or []) | set(regex_extract(text)["urls"]))
        out["shortener"] = bool(out.get("shortener")) or any(u.lower().replace("https://", "").replace("http://", "").startswith(SHORTENERS) for u in out["urls"])
        s.set("signals", json.dumps(out, ensure_ascii=False))
        return out


def regex_extract(text: str) -> dict:
    t = text
    urls = [u.rstrip(".,)") for u in URL_RE.findall(t)]
    money = None
    if re.search(MONEY, t, re.I) or any(re.search(p, t, re.I) for p in METHODS.values()):
        amt = re.search(r"[\d,]{2,}", re.search(MONEY, t, re.I).group(0)) if re.search(MONEY, t, re.I) else None
        method = next((m for m, p in METHODS.items() if re.search(p, t, re.I)), "other")
        money = {"amount": float(amt.group(0).replace(",", "")) if amt else None, "method": method}
    name_m = NAME_RE.search(t)
    brand = next((b for b, p in BRANDS.items() if re.search(p, t, re.I)), None)
    return {
        "urls": urls,
        "claims_family": bool(re.search(FAMILY_WORDS, t, re.I)),
        "claimed_name": next(g for g in name_m.groups() if g).title() if name_m else None,
        "money_request": money,
        "secrecy": bool(re.search(SECRECY, t, re.I)),
        "urgency": bool(re.search(URGENCY, t, re.I)),
        "brand": brand,
        "shortener": any(u.lower().replace("https://", "").replace("http://", "").startswith(SHORTENERS) for u in urls),
        "language": detect_lang(t),
        "remote_access": bool(re.search(REMOTE_ACCESS, t, re.I)),
        "tech_support_claim": bool(re.search(TECH_SUPPORT, t, re.I)),
        "callback_number": (CALLBACK_RE.search(t).group(0).strip() if CALLBACK_RE.search(t) else None),
    }


def detect_lang(text: str) -> str:
    if re.search(r"[\u0C00-\u0C7F]", text):  # Telugu script
        return "te"
    es = len(re.findall(r"\b(el|la|su|que|de|por|para|usted|está|cuenta|mamá|dinero|no|es|en)\b", text.lower()))
    en = len(re.findall(r"\b(the|your|is|to|and|you|account|mom|money|please|of)\b", text.lower()))
    return "es" if es > en else "en"


def _bedrock(text: str) -> dict:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
    resp = client.converse(
        modelId=config.BEDROCK_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": PROMPT + text}]}],
        inferenceConfig={"maxTokens": 400, "temperature": 0},
    )
    raw = resp["output"]["message"]["content"][0]["text"]
    raw = raw[raw.find("{") : raw.rfind("}") + 1]
    return json.loads(raw)


def ocr_image(image_bytes: bytes) -> str:
    """Textract for screenshots Rosa forwards (MMS)."""
    if not (config.USE_TEXTRACT and not config.FORCE_MOCK):
        return ""
    import boto3

    tx = boto3.client("textract", region_name=config.AWS_REGION)
    r = tx.detect_document_text(Document={"Bytes": image_bytes})
    return " ".join(b["Text"] for b in r["Blocks"] if b["BlockType"] == "LINE")


EMBED_MODEL = "amazon.titan-embed-text-v2:0"


def embed(text: str) -> list[float] | None:
    """Bedrock Titan embedding (1024-d) for 'same scam, reworded' matching in SurrealDB."""
    if not config.live(config.BEDROCK_MODEL_ID):
        return None
    try:
        import boto3

        c = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
        r = c.invoke_model(modelId=EMBED_MODEL, body=json.dumps({"inputText": text[:4000], "dimensions": 1024, "normalize": True}))
        return json.loads(r["body"].read())["embedding"]
    except Exception:
        return None
