"""All settings come from env. An unset sponsor key = that sponsor runs in mock mode."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # optional

    _root = Path(__file__).resolve().parent.parent
    # Process env always wins (run.py mock / tests set GUARDIAN_MOCK=1); then .env.local, then .env. Both gitignored.
    load_dotenv(_root / ".env.local")
    load_dotenv(_root / ".env")
except Exception:
    pass


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


FORCE_MOCK = _get("GUARDIAN_MOCK", "0") == "1"

# --- Daytona + Anchor (Hero 3) ---
DAYTONA_API_KEY = _get("DAYTONA_API_KEY")
ANCHOR_API_KEY = _get("ANCHOR_API_KEY")
# daytona = run job inside a Daytona sandbox; local = run job here (still uses Anchor); mock = canned result
DETONATE_MODE = _get("DETONATE_MODE", "daytona")
DETONATE_TIMEOUT_S = int(_get("DETONATE_TIMEOUT_S", "20"))

# --- ElevenLabs + Twilio (calls + SMS) ---
ELEVENLABS_API_KEY = _get("ELEVENLABS_API_KEY")
ELEVENLABS_PHONE_NUMBER_ID = _get("ELEVENLABS_PHONE_NUMBER_ID")
WARNING_AGENT_ID_ES = _get("WARNING_AGENT_ID_ES")
WARNING_AGENT_ID_EN = _get("WARNING_AGENT_ID_EN")
WARNING_AGENT_ID_TE = _get("WARNING_AGENT_ID_TE")
VERIFY_AGENT_ID = _get("VERIFY_AGENT_ID")
SECOND_KEY_AGENT_ID = _get("SECOND_KEY_AGENT_ID")
TWILIO_ACCOUNT_SID = _get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = _get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = _get("TWILIO_FROM")
PUBLIC_BASE_URL = _get("PUBLIC_BASE_URL", "http://localhost:8000")
UI_BASE_URL = _get("UI_BASE_URL", "http://localhost:3000")

# Verify-by-callback timing (seconds). Shorten for the stage.
VERIFY_RETRY_AFTER_S = int(_get("VERIFY_RETRY_AFTER_S", "120"))
ADMIN_ESCALATE_AFTER_S = int(_get("ADMIN_ESCALATE_AFTER_S", "900"))

# --- SurrealDB ---
SURREAL_URL = _get("SURREAL_URL")  # e.g. http://localhost:8001
SURREAL_USER = _get("SURREAL_USER", "root")
SURREAL_PASS = _get("SURREAL_PASS", "root")
SURREAL_NS = _get("SURREAL_NS", "guardian")
SURREAL_DB = _get("SURREAL_DB", "guardian")

# --- AWS ---
BEDROCK_MODEL_ID = _get("BEDROCK_MODEL_ID")  # e.g. a Claude model id enabled in your account
AWS_REGION = _get("AWS_REGION", "us-east-1")
USE_TEXTRACT = _get("USE_TEXTRACT", "0") == "1"

# --- Arize AX (cloud; preferred) or self-hosted Phoenix (fallback) ---
ARIZE_SPACE_ID = _get("ARIZE_SPACE_ID")
ARIZE_API_KEY = _get("ARIZE_API_KEY")
ARIZE_PROJECT = _get("ARIZE_PROJECT", "guardian")
PHOENIX_COLLECTOR_ENDPOINT = _get("PHOENIX_COLLECTOR_ENDPOINT")  # e.g. http://localhost:6006
PHOENIX_PROJECT = _get("PHOENIX_PROJECT", "guardian")

# --- SurrealDB Agent Memory (hosted) ---
SURREAL_MEMORY_URL = _get("SURREAL_MEMORY_URL")  # context host, e.g. https://xxxx.agent-memory.surrealdb.com
SURREAL_MEMORY_KEY = _get("SURREAL_MEMORY_KEY")  # sp-...
SURREAL_MEMORY_CONTEXT = _get("SURREAL_MEMORY_CONTEXT")

# --- Mock behaviour (for rehearsal without phones) ---
MOCK_VERIFY_OUTCOME = _get("MOCK_VERIFY_OUTCOME", "denied")  # denied | confirmed | no_answer
MOCK_KEY_DECISION = _get("MOCK_KEY_DECISION", "")  # "" = wait for UI, or decline | approve
MOCK_CALL_SPEED = float(_get("MOCK_CALL_SPEED", "1.0"))  # <1 = faster scripted calls


def live(*keys: str) -> bool:
    """True when every key is set and mock is not forced."""
    return not FORCE_MOCK and all(keys)


def status() -> dict:
    return {
        "daytona": live(DAYTONA_API_KEY) and DETONATE_MODE == "daytona",
        "anchor": live(ANCHOR_API_KEY) and DETONATE_MODE != "mock",
        "elevenlabs": live(ELEVENLABS_API_KEY, ELEVENLABS_PHONE_NUMBER_ID),
        "twilio_sms": live(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM),
        "surrealdb": live(SURREAL_URL),
        "bedrock": live(BEDROCK_MODEL_ID),
        "arize": live(ARIZE_SPACE_ID, ARIZE_API_KEY),
        "phoenix": live(PHOENIX_COLLECTOR_ENDPOINT) and not live(ARIZE_SPACE_ID, ARIZE_API_KEY),
        "surreal_memory": live(SURREAL_MEMORY_URL, SURREAL_MEMORY_KEY, SURREAL_MEMORY_CONTEXT),
    }
