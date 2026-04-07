"""Settings loaded from environment / .env file."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# .env immer relativ zu diesem File suchen — egal von wo der Bot gestartet wird
_ENV_PATH = Path(__file__).parent.parent / ".env"


def _load_dotenv() -> None:
    if not _ENV_PATH.exists():
        return
    with _ENV_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key.isidentifier() or all(c.isalnum() or c == "_" for c in key):
                if key not in os.environ:
                    os.environ[key] = value


@dataclass
class Settings:
    telegram_bot_token: str
    authorized_user_id: int
    admin_user_id: int
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    llm_model: str = "gpt-4o-mini"
    stt_provider: str = "mock"
    whisper_model: str = "small"
    tts_provider: str = "mock"
    elevenlabs_api_key: Optional[str] = None
    voice_id_vitali: Optional[str] = None
    voice_id_dering: Optional[str] = None
    voice_id_imperator: Optional[str] = None
    database_path: str = "data/natalia_bot.db"
    log_file: str = "logs/bot.log"
    support_codeword: str = "hilfe123"
    daily_reminder_time: str = "09:00"
    timezone: str = "Europe/Berlin"

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        env = os.environ
        token = env.get("TELEGRAM_BOT_TOKEN")
        user_id = env.get("AUTHORIZED_USER_ID")
        admin_id = env.get("ADMIN_USER_ID")
        if not token or not user_id or not admin_id:
            raise RuntimeError(
                "Mandatory env vars missing: TELEGRAM_BOT_TOKEN, AUTHORIZED_USER_ID, ADMIN_USER_ID"
            )
        try:
            uid = int(user_id)
            aid = int(admin_id)
        except ValueError as exc:
            raise RuntimeError("AUTHORIZED_USER_ID and ADMIN_USER_ID must be integers") from exc
        return cls(
            telegram_bot_token=token,
            authorized_user_id=uid,
            admin_user_id=aid,
            llm_provider=env.get("LLM_PROVIDER", "openai"),
            openai_api_key=env.get("OPENAI_API_KEY"),
            openai_base_url=env.get("OPENAI_BASE_URL"),
            llm_model=env.get("LLM_MODEL", "gpt-4o-mini"),
            stt_provider=env.get("STT_PROVIDER", "mock"),
            whisper_model=env.get("WHISPER_MODEL", "small"),
            tts_provider=env.get("TTS_PROVIDER", "mock"),
            elevenlabs_api_key=env.get("ELEVENLABS_API_KEY"),
            voice_id_vitali=env.get("VOICE_ID_VITALI"),
            voice_id_dering=env.get("VOICE_ID_DERING"),
            voice_id_imperator=env.get("VOICE_ID_IMPERATOR"),
            database_path=env.get("DATABASE_PATH", "data/natalia_bot.db"),
            log_file=env.get("LOG_FILE", "logs/bot.log"),
            support_codeword=env.get("SUPPORT_CODEWORD", "hilfe123"),
            daily_reminder_time=env.get("DAILY_REMINDER_TIME", "09:00"),
            timezone=env.get("TIMEZONE", "Europe/Berlin"),
        )
