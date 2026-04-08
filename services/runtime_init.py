"""Initialisiert alle Services und fuehrt Auto-Migrations durch."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auto-Migration beim Start
# ---------------------------------------------------------------------------

_MIGRATIONS_DIR = Path(__file__).parent.parent / "db" / "migrations"
_APPLIED_TABLE  = "__applied_migrations"


def _run_auto_migrations(db_path: str) -> None:
    """Fuehrt alle noch nicht angewendeten SQL-Migrations automatisch aus."""
    if not _MIGRATIONS_DIR.exists():
        logger.debug("Kein migrations/ Ordner — ueberspringe.")
        return

    sql_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        return

    with sqlite3.connect(db_path) as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {_APPLIED_TABLE} (
                name TEXT PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

        applied = {
            row[0] for row in
            conn.execute(f"SELECT name FROM {_APPLIED_TABLE}").fetchall()
        }

        for sql_file in sql_files:
            name = sql_file.name
            if name in applied:
                logger.debug("Migration bereits angewendet: %s", name)
                continue

            logger.info("Wende Migration an: %s", name)
            sql = sql_file.read_text(encoding="utf-8")
            try:
                conn.executescript(sql)
                conn.execute(
                    f"INSERT INTO {_APPLIED_TABLE} (name) VALUES (?)", (name,)
                )
                conn.commit()
                logger.info("Migration erfolgreich: %s", name)
            except Exception as e:
                logger.error("Migration fehlgeschlagen (%s): %s", name, e)
                # Nicht abbrechen — naechste Migration versuchen


# ---------------------------------------------------------------------------
# Service-Initialisierung
# ---------------------------------------------------------------------------

def init_services(settings) -> dict:
    """Erstellt und gibt alle Services als Dict zurueck."""
    from config.settings import Settings
    assert isinstance(settings, Settings)

    # 1. Auto-Migrations
    _run_auto_migrations(settings.database_path)

    # 2. DB-Repos
    from db.user_repo    import UserRepository
    from db.memory_repo  import MemoryRepository
    from db.vocab_repo   import VocabRepository

    user_repo   = UserRepository(settings.database_path)
    memory_repo = MemoryRepository(settings.database_path)
    vocab_repo  = VocabRepository(settings.database_path)

    # 3. LLM
    from services.llm.openai_provider import OpenAIProvider
    llm = OpenAIProvider(
        api_key  = settings.openai_api_key,
        base_url = settings.openai_base_url,
        model    = settings.llm_model,
    )

    # 4. STT
    stt = None
    if settings.stt_provider == "whisper_local":
        try:
            from services.stt.whisper_local import WhisperLocalSTT
            stt = WhisperLocalSTT(model_size=settings.whisper_model)
            logger.info("STT: Whisper local (%s)", settings.whisper_model)
        except Exception as e:
            logger.warning("Whisper STT nicht verfuegbar: %s", e)

    if stt is None:
        try:
            from services.stt.groq_stt import GroqSTT
            stt = GroqSTT(api_key=settings.groq_api_key)
            logger.info("STT: Groq Fallback")
        except Exception as e:
            logger.warning("Groq STT nicht verfuegbar: %s", e)

    # 5. TTS + Cache
    tts = None
    if settings.tts_provider == "elevenlabs":
        try:
            from services.tts.elevenlabs_tts import ElevenLabsTTS
            _raw_tts = ElevenLabsTTS(
                api_key       = settings.elevenlabs_api_key,
                audio_temp_dir= settings.audio_temp_dir,
            )
            # TTS-Cache aktivieren
            from services.tts_cache import TTSCache
            tts = TTSCache(_raw_tts, cache_dir=settings.audio_cache_dir)
            logger.info("TTS: ElevenLabs + Cache (%s)", settings.audio_cache_dir)
        except Exception as e:
            logger.warning("ElevenLabs TTS nicht verfuegbar: %s", e)

    # 6. Voice-Pipeline
    from services.voice_pipeline import VoicePipeline
    vp = VoicePipeline(
        stt      = stt,
        tts      = tts,
        voice_id = settings.voice_id_imperator,
    )

    # 7. Lesson-Planner
    from services.lesson_planner import LessonPlanner
    lesson_planner = LessonPlanner(
        db_path   = settings.database_path,
        vocab_repo= vocab_repo,
    )

    # 8. Dialogue-Router
    from services.dialogue_router import DialogueRouter
    dialogue_router = DialogueRouter(
        llm_provider = llm,
        user_repo    = user_repo,
        memory_repo  = memory_repo,
    )

    # 9. Streak
    from services.streak import StreakService
    streak = StreakService(settings.database_path)

    services = {
        "llm":             llm,
        "stt":             stt,
        "tts":             tts,
        "voice_pipeline":  vp,
        "user_repo":       user_repo,
        "memory_repo":     memory_repo,
        "vocab_repo":      vocab_repo,
        "lesson_planner":  lesson_planner,
        "dialogue_router": dialogue_router,
        "streak":          streak,
    }

    logger.info("Services initialisiert: %s", list(services.keys()))
    return services
