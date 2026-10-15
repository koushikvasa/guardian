"""Deterministic verdict. The LLM only extracts signals; this file decides.

Every reason shown to a family member cites a rule id from RULES, which is what the
grounding eval checks.
"""
from dataclasses import dataclass, field

RULES = {
    "herd_match": (100, {"en": "Another family already reported this exact scam.", "es": "Otra familia ya reportó esta misma estafa.", "te": "ఇదే మోసాన్ని ఇంకో కుటుంబం ఇప్పటికే రిపోర్ట్ చేసింది."}),
    "remembered_scam": (60, {"en": "Guardian remembers: the same {what} was a scam on {date}.", "es": "Guardian lo recuerda: el mismo {what} fue una estafa el {date}.", "te": "Guardian గుర్తుంచుకుంది: ఇదే {what} {date}న మోసం."}),
    "credential_form_new_domain": (40, {"en": "Asks for passwords or card numbers on a site created {age} days ago.", "es": "Pide contraseña o tarjeta en un sitio creado hace {age} días.", "te": "{age} రోజుల క్రితం సృష్టించిన సైట్‌లో పాస్‌వర్డ్ లేదా కార్డ్ నంబర్ అడుగుతోంది."}),
    "untraceable_payment": (35, {"en": "Wants {method}, which can't be undone.", "es": "Pide {method}, que no se puede deshacer.", "te": "{method} అడుగుతోంది, దాన్ని వెనక్కి తీసుకోలేం."}),
    "brand_domain_mismatch": (30, {"en": "Looks like {brand}, but the address is {domain}.", "es": "Parece de {brand}, pero la dirección es {domain}.", "te": "{brand} లాగా కనిపిస్తోంది, కానీ చిరునామా {domain}."}),
    "family_claim_unsaved_number": (25, {"en": "Claims to be {name}, from a number that isn't saved.", "es": "Dice ser {name}, desde un número que no está guardado.", "te": "సేవ్ చేయని నంబర్ నుంచి {name} అని చెప్పుకుంటోంది."}),
    "secrecy_request": (20, {"en": "Asks to keep it secret.", "es": "Pide que no le diga a nadie.", "te": "రహస్యంగా ఉంచమని అడుగుతోంది."}),
    "shortener_or_redirects": (15, {"en": "Hidden behind a short link and {n} redirects.", "es": "Escondido detrás de un enlace corto y {n} redirecciones.", "te": "షార్ట్ లింక్ వెనుక, {n} రీడైరెక్ట్‌లతో దాచి ఉంది."}),
    "urgency": (12, {"en": "Pushes you to act right now.", "es": "Le presiona para actuar ya.", "te": "ఇప్పుడే చేయమని ఒత్తిడి చేస్తోంది."}),
    "trusted_contact": (-40, {"en": "Comes from a saved family number.", "es": "Viene de un número de familia guardado.", "te": "సేవ్ చేసిన కుటుంబ నంబర్ నుంచి వచ్చింది."}),
    "official_domain": (-50, {"en": "Goes to the real {brand} website.", "es": "Lleva al sitio real de {brand}.", "te": "అసలైన {brand} వెబ్‌సైట్‌కి వెళ్తుంది."}),
}

UNTRACEABLE = {"gift_card", "wire", "crypto", "zelle", "western_union", "cash_courier", "bitcoin_atm"}
METHOD_NAMES = {
    "en": {"gift_card": "gift cards", "wire": "a wire transfer", "crypto": "crypto", "zelle": "Zelle", "western_union": "Western Union", "cash_courier": "cash by courier", "bitcoin_atm": "a Bitcoin ATM"},
    "es": {"gift_card": "tarjetas de regalo", "wire": "una transferencia", "crypto": "cripto", "zelle": "Zelle", "western_union": "Western Union", "cash_courier": "efectivo por mensajero", "bitcoin_atm": "un cajero de Bitcoin"},
    "te": {"gift_card": "గిఫ్ట్ కార్డులు", "wire": "వైర్ ట్రాన్స్‌ఫర్", "crypto": "క్రిప్టో", "zelle": "Zelle", "western_union": "Western Union", "cash_courier": "కొరియర్ ద్వారా నగదు", "bitcoin_atm": "బిట్‌కాయిన్ ATM"},
}
WHAT_NAMES = {"en": {"link": "link", "sender": "sender", "story": "story"}, "es": {"link": "enlace", "sender": "remitente", "story": "cuento"},
              "te": {"link": "లింక్", "sender": "పంపినవారు", "story": "కథ"}}
RELATIVE = {"en": "a relative", "es": "un familiar", "te": "బంధువు"}
SAFE_MAX, SUSPICIOUS_MAX = 29, 59


@dataclass
class Verdict:
    score: int
    label: str  # safe | suspicious | scam
    critical: bool
    fired: list[dict] = field(default_factory=list)  # [{rule, weight, reason}]

    def reasons(self) -> list[str]:
        return [f["reason"] for f in self.fired if f["weight"] > 0]


def evaluate(signals: dict, sender: dict, detonation: dict | None, herd_hits: int, lang: str = "en",
             memory: dict | None = None) -> Verdict:
    """memory: {"what": link|sender|story, "date": YYYY-MM-DD} when Agent Memory holds a matching scam verdict."""
    lang = lang if lang in ("en", "es", "te") else "en"
    fired: list[dict] = []

    def fire(rule: str, **fmt):
        weight, text = RULES[rule]
        en = dict(fmt)
        if "method" in en:  # method names are localized; give Daniel the English one
            en["method"] = next((METHOD_NAMES["en"][k] for k, v in METHOD_NAMES[lang].items() if v == fmt["method"]), fmt["method"])
        if en.get("name") in RELATIVE.values():
            en["name"] = "a relative"
        if "what" in en:
            en["what"] = next((k for k, v in WHAT_NAMES[lang].items() if v == fmt["what"]), fmt["what"])
        fired.append({"rule": rule, "weight": weight, "reason": text[lang].format(**fmt), "reason_en": text["en"].format(**en)})

    if herd_hits > 0:
        fire("herd_match")
    if memory and memory.get("what") in WHAT_NAMES["en"]:
        fire("remembered_scam", what=WHAT_NAMES[lang][memory["what"]], date=memory.get("date") or "")

    d = detonation or {}
    age = d.get("domain_age_days")
    if d.get("form_fields") and _asks_credentials(d["form_fields"]) and age is not None and age < 30:
        fire("credential_form_new_domain", age=age)

    money = signals.get("money_request") or {}
    method = (money.get("method") or "").lower()
    if method in UNTRACEABLE:
        fire("untraceable_payment", method=METHOD_NAMES[lang].get(method, method))

    brand = (d.get("brands") or [None])[0] or signals.get("brand")
    domain = d.get("final_domain")
    if brand and domain:
        if d.get("official_domain"):
            fire("official_domain", brand=brand)
        else:
            fire("brand_domain_mismatch", brand=brand, domain=domain)

    if signals.get("claims_family") and not sender.get("saved"):
        fire("family_claim_unsaved_number", name=signals.get("claimed_name") or RELATIVE[lang])

    if signals.get("secrecy"):
        fire("secrecy_request")

    n_redirects = len(d.get("redirects") or [])
    if signals.get("shortener") or d.get("shortener") or n_redirects >= 3:
        fire("shortener_or_redirects", n=n_redirects)

    if signals.get("urgency"):
        fire("urgency")

    if sender.get("trusted") and not signals.get("claims_family_from_other_number"):
        fire("trusted_contact")

    score = max(0, sum(f["weight"] for f in fired))
    label = "safe" if score <= SAFE_MAX else "suspicious" if score <= SUSPICIOUS_MAX else "scam"
    critical = bool(money) and score >= 30
    return Verdict(score=score, label=label, critical=critical, fired=fired)


def _asks_credentials(fields: list[str]) -> bool:
    keys = ("pass", "contraseña", "contrasena", "card", "tarjeta", "cvv", "ssn", "pin", "código", "codigo", "otp")
    return any(any(k in f.lower() for k in keys) for f in fields)
