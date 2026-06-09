import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


@dataclass(frozen=True)
class Settings:
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    persona_name: str = os.getenv("PERSONA_NAME", "Kuldeep Sharma")
    persona_email: str = os.getenv("PERSONA_EMAIL", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "openai")
    openai_embedding_api_key: str = os.getenv("OPENAI_EMBEDDING_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    calendar_provider: str = os.getenv("CALENDAR_PROVIDER", "calcom")
    calcom_api_key: str = env_first("CALCOM_API_KEY", "CAL_API_KEY")
    calcom_event_type_id: str = env_first("CALCOM_EVENT_TYPE_ID", "CAL_EVENT_TYPE_ID")
    calcom_timezone: str = env_first("CALCOM_TIMEZONE", "CAL_TIMEZONE", default="Asia/Kolkata")
    voice_webhook_secret: str = os.getenv("VOICE_WEBHOOK_SECRET", "")


settings = Settings()
