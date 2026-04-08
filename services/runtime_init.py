"""Initialisiert alle Services und fuehrt Auto-Migrations durch."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent.parent / "db" / "migrations"
_APPLIED_TABLE  = "__applied_migrations"


def _run_auto_migrations(db_path: str) -> None:
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
        applied = {r[0] for r in conn.execute(f"SELECT name FROM {_APPLIED_TABLE}").fetchall()}
        for f in sql_files:
            if f.name in applied:
                continue
            logger.info("Migration: %s", f.name)
            try:
                conn.executescript(f.read_text(encoding="utf-8"))
                conn.execute(f"INSERT INTO {_APPLIED_TABLE} (name) VALUES (?)", (f.name,))
                conn.commit()
            except Exception as e:
                logger.error("Migration fehlgeschlagen (%s): %s", f.name, e)


def init_services(settings) -> dict:
    """Erstellt und gibt alle Services als Dict zurueck."""
    from config.settings import Settings
    assert isinstance(settings, Settings)

    _run_auto_migrations(settings.database_path)

    # Repositories — liegen unter db/repositories/
    from db.repositories.user_repository   import UserRepository
    from db.repositories.memory_repository import MemoryRepository

    user_repo   = UserRepository(settings.database_path)
    memory_repo = MemoryRepository(settings.database_path)

    # VocabRepository: optional — falls vorhanden nutzen, sonst None
    vocab_repo = None
    try:
        from db.repositories.vocab_repository import VocabRepository
        vocab_repo = VocabRepository(settings.database_path)
        logger.info("VocabRepository geladen.")
    except ImportError:
        logger.info("Kein VocabRepository gefunden — LessonPlanner nutzt direkten DB-Zugriff.")

    # LLM
    from services.llm.openai_provider import OpenAIProvider
    llm = OpenAIProvider(
        api_key  = settings.openai_api_key,
        base_url = settings.openai_base_url,
        model    = settings.llm_model,
    )

    # STT
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

    # TTS — einheitlich ueber Factory
    from services.tts import create_tts_provider
    tts = create_tts_provider(settings)

    # Voice-Pipeline
    from services.voice_pipeline import VoicePipeline
    vp = VoicePipeline(
        stt      = stt,
        tts      = tts,
        voice_id = settings.voice_id_imperator,
    )
    logger.info("VoicePipeline: voice_id=%r", vp.voice_id)

    # Lesson-Planner
    from services.lesson_planner import LessonPlanner
    lesson_planner = LessonPlanner(
        db_path    = settings.database_path,
        vocab_repo = vocab_repo,  # kann None sein
    )

    # Dialogue-Router
    from services.dialogue_router import DialogueRouter
    dialogue_router = DialogueRouter(
        llm_provider = llm,
        user_repo    = user_repo,
        memory_repo  = memory_repo,
    )

    # Streak
    streak = None
    try:
        from services.streak import StreakService
        streak = StreakService(settings.database_path)
    except ImportError:
        logger.debug("StreakService nicht gefunden — ueberspringe.")

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
    logger.info("Services bereit: %s", list(services.keys()))
    return services


# Alias fuer app/main.py Kompatibilitaet
initialise_services = init_services
