"""Every word Guardian texts a family member. Spanish, English and Telugu."""

T = {
    "ack": {
        "es": "Guardian: Recibido. Lo estoy revisando. No toque el enlace ni conteste todavía.",
        "en": "Guardian: Got it. I'm checking it now. Don't tap the link or reply yet.",
        "te": "Guardian: అందింది. నేను చూస్తున్నాను. ఇప్పుడే లింక్ నొక్కొద్దు, జవాబు ఇవ్వొద్దు.",
    },
    "hold_money": {
        "es": "Guardian: No envíe dinero todavía. Estoy llamando a {name} a su número guardado.",
        "en": "Guardian: Don't send any money yet. I'm calling {name} on their saved number.",
        "te": "Guardian: ఇప్పుడే డబ్బు పంపొద్దు. {name}కి వాళ్ళ సేవ్ చేసిన నంబర్‌కి కాల్ చేస్తున్నాను.",
    },
    "safe": {
        "es": "Guardian: Lo revisé y parece seguro. {reason}",
        "en": "Guardian: I checked it and it looks safe. {reason}",
        "te": "Guardian: చూశాను, ఇది సురక్షితంగా ఉంది. {reason}",
    },
    "suspicious": {
        "es": "Guardian: Esto parece sospechoso. No toque el enlace. {reasons}",
        "en": "Guardian: This looks suspicious. Don't tap the link. {reasons}",
        "te": "Guardian: ఇది అనుమానంగా ఉంది. లింక్ నొక్కొద్దు. {reasons}",
    },
    "scam_calling": {
        "es": "Guardian: Es una estafa. No toque nada. La llamo ahora para explicarle.",
        "en": "Guardian: This is a scam. Don't tap anything. I'm calling you now to explain.",
        "te": "Guardian: ఇది మోసం. ఏదీ నొక్కొద్దు. వివరించడానికి ఇప్పుడే మీకు కాల్ చేస్తున్నాను.",
    },
    "verify_denied": {
        "es": "Guardian: {name} está bien y no le escribió. Era una estafa. No envíe nada y no conteste.",
        "en": "Guardian: {name} is fine and didn't message you. It was a scam. Don't send anything or reply.",
        "te": "Guardian: {name} బాగానే ఉన్నారు, మీకు మెసేజ్ పంపలేదు. ఇది మోసం. ఏమీ పంపొద్దు, జవాబు ఇవ్వొద్దు.",
    },
    "verify_confirmed": {
        "es": "Guardian: {name} dice que sí fue él. Aun así, no envíe dinero hasta que {name} la llame directamente.",
        "en": "Guardian: {name} says it was them. Still, don't send money until {name} calls you directly.",
        "te": "Guardian: {name} అది తానేనని చెప్పారు. అయినా, {name} మీకు నేరుగా కాల్ చేసే వరకు డబ్బు పంపొద్దు.",
    },
    "verify_no_answer": {
        "es": "Guardian: Todavía no contesta {name}. Sigo intentando. No envíe nada mientras tanto.",
        "en": "Guardian: {name} hasn't picked up yet. I'm still trying. Don't send anything meanwhile.",
        "te": "Guardian: {name} ఇంకా ఫోన్ ఎత్తలేదు. మళ్ళీ ప్రయత్నిస్తున్నాను. అప్పటి వరకు ఏమీ పంపొద్దు.",
    },
    "key_waiting": {
        "es": "Guardian: Antes de enviar ${amount}, {guardian} tiene que dar la segunda llave. Lo estoy llamando.",
        "en": "Guardian: Before sending ${amount}, {guardian} needs to give the second key. I'm calling them now.",
        "te": "Guardian: ${amount} పంపే ముందు {guardian} రెండో తాళం ఇవ్వాలి. ఇప్పుడే కాల్ చేస్తున్నాను.",
    },
    "key_declined": {
        "es": "Guardian: {guardian} dijo que no lo envíe. Es una estafa. No envíe nada.",
        "en": "Guardian: {guardian} said don't send it. It's a scam. Don't send anything.",
        "te": "Guardian: {guardian} పంపొద్దని చెప్పారు. ఇది మోసం. ఏమీ పంపొద్దు.",
    },
    "key_approved": {
        "es": "Guardian: {guardian} dio la segunda llave. Si usted también está segura, puede continuar.",
        "en": "Guardian: {guardian} gave the second key. If you're sure too, you can go ahead.",
        "te": "Guardian: {guardian} రెండో తాళం ఇచ్చారు. మీకూ నమ్మకం ఉంటే, కొనసాగించవచ్చు.",
    },
    "help_note": {
        "es": "Guardian: ¿Quiere avisarles a sus amigas? Grabé su historia en 20 segundos: {link}",
        "en": "Guardian: Want to warn your friends? Here's your story in 20 seconds: {link}",
        "te": "Guardian: మీ స్నేహితులను హెచ్చరించాలనుకుంటున్నారా? మీ కథ 20 సెకన్లలో: {link}",
    },
}


def t(key: str, lang: str, **kw) -> str:
    lang = lang if lang in ("es", "en", "te") else "en"
    return T[key][lang].format(**kw)
