"""Deterministic verdict. The LLM only extracts signals; this file decides.

Every reason shown to a family member cites a rule id from RULES, which is what the
grounding eval checks.
"""
from dataclasses import dataclass, field

RULES = {
    "herd_match": (100, {"en": "Another family already reported this exact scam.", "es": "Otra familia ya reportó esta misma estafa."}),
    "credential_form_new_domain": (40, {"en": "Asks for passwords or card numbers on a site created {age} days ago.", "es": "Pide contraseña o tarjeta en un sitio creado hace {age} días."}),
    "untraceable_payment": (35, {"en": "Wants {method}, which can't be undone.", "es": "Pide {method}, que no se puede deshacer."}),
    "brand_domain_mismatch": (30, {"en": "Looks like {brand}, but the address is {domain}.", "es": "Parece de {brand}, pero la dirección es {domain}."}),
    "family_claim_unsaved_number": (25, {"en": "Claims to be {name}, from a number that isn't saved.", "es": "Dice ser {name}, desde un número que no está guardado."}),
    "secrecy_request": (20, {"en": "Asks to keep it secret.", "es": "Pide que no le diga a nadie."}),
    "shortener_or_redirects": (15, {"en": "Hidden behind a short link and {n} redirects.", "es": "Escondido detrás de un enlace corto y {n} redirecciones."}),
    "urgency": (12, {"en": "Pushes you to act right now.", "es": "Le presiona para actuar ya."}),
    "trusted_contact": (-40, {"en": "Comes from a saved family number.", "es": "Viene de un número de familia guardado."}),
    "official_domain": (-50, {"en": "Goes to the real {brand} website.", "es": "Lleva al sitio real de {brand}."}),
}

UNTRACEABLE = {"gift_card", "wire", "crypto", "zelle", "western_union", "cash_courier", "bitcoin_atm"}
METHOD_NAMES = {
    "en": {"gift_card": "gift cards", "wire": "a wire transfer", "crypto": "crypto", "zelle": "Zelle", "western_union": "Western Union", "cash_courier": "cash by courier", "bitcoin_atm": "a Bitcoin ATM"},
    "es": {"gift_card": "tarjetas de regalo", "wire": "una transferencia", "crypto": "cripto", "zelle": "Zelle", "western_union": "Western Union", "cash_courier": "efectivo por mensajero", "bitcoin_atm": "un cajero de Bitcoin"},
}
SAFE_MAX, SUSPICIOUS_MAX = 29, 59


@dataclass
class Verdict:
    score: int
    label: str  # safe | suspicious | scam
    critical: bool
    fired: list[dict] = field(default_factory=list)  # [{rule, weight, reason}]

    def reasons(self) -> list[str]:
        return [f["reason"] for f in self.fired if f["weight"] > 0]


def evaluate(signals: dict, sender: dict, detonation: dict | None, herd_hits: int, lang: str = "en") -> Verdict:
    lang = lang if lang in ("en", "es") else "en"
    fired: list[dict] = []

    def fire(rule: str, **fmt):
        weight, text = RULES[rule]
        en = dict(fmt)
        if "method" in en:  # method names are localized; give Daniel the English one
            en["method"] = next((METHOD_NAMES["en"][k] for k, v in METHOD_NAMES[lang].items() if v == fmt["method"]), fmt["method"])
        if en.get("name") == "un familiar":
            en["name"] = "a relative"
        fired.append({"rule": rule, "weight": weight, "reason": text[lang].format(**fmt), "reason_en": text["en"].format(**en)})

    if herd_hits > 0:
        fire("herd_match")

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
        fire("family_claim_unsaved_number", name=signals.get("claimed_name") or ("a relative" if lang == "en" else "un familiar"))

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
