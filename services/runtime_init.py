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

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------
    from db.repositories.user_repository   import UserRepository
    from db.repositories.memory_repository import MemoryRepository

    user_repo   = UserRepository(settings.database_path)
    memory_repo = MemoryRepository(settings.database_path)

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------
    from services.llm.openai_provider import OpenAIProvider
    llm = OpenAIProvider(
        api_key  = settings.openai_api_key,
        base_url = settings.openai_base_url,
        model    = settings.llm_model,
    )

    # ------------------------------------------------------------------
    # STT  (Datei: whisper_provider.py -> class WhisperLocalProvider)
    #       (Datei: groq_provider.py   -> class GroqSTTProvider)
    # ------------------------------------------------------------------
    stt = None
    if settings.stt_provider == "whisper_local":
        try:
            from services.stt.whisper_provider import WhisperLocalProvider
            stt = WhisperLocalProvider(model_size=settings.whisper_model)
            logger.info("STT: Whisper local (%s)", settings.whisper_model)
        except Exception as e:
            logger.warning("Whisper STT nicht verfuegbar: %s", e)

    if stt is None:
        try:
            from services.stt.groq_provider import GroqSTTProvider
            stt = GroqSTTProvider(api_key=settings.groq_api_key)
            logger.info("STT: Groq Fallback aktiv")
        except Exception as e:
            logger.error("Groq STT nicht verfuegbar: %s", e)

    if stt is None:
        logger.error("KEIN STT Provider verfuegbar — Sprachnachrichten funktionieren nicht!")

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------
    from services.tts import create_tts_provider
    tts = create_tts_provider(settings)

    # ------------------------------------------------------------------
    # Voice-Pipeline
    # ------------------------------------------------------------------
    from services.voice_pipeline import VoicePipeline
    vp = VoicePipeline(
        stt      = stt,
        tts      = tts,
        voice_id = settings.voice_id_imperator,
    )
    logger.info("VoicePipeline: voice_id=%r, stt=%s", vp.voice_id, type(stt).__name__ if stt else "None")

    # ------------------------------------------------------------------
    # Lesson-Planner
    # ------------------------------------------------------------------
    from services.lesson_planner import LessonPlanner
    lesson_planner = LessonPlanner(db_path=settings.database_path)

    # ------------------------------------------------------------------
    # Dialogue-Router
    # ------------------------------------------------------------------
    from services.dialogue_router import DialogueRouter
    dialogue_router = DialogueRouter(
        llm_provider = llm,
        user_repo    = user_repo,
        memory_repo  = memory_repo,
    )

    # ------------------------------------------------------------------
    # Streak  (Datei: streak_service.py -> class StreakService)
    # ------------------------------------------------------------------
    streak = None
    try:
        from services.streak_service import StreakService
        streak = StreakService(settings.database_path)
        logger.info("StreakService bereit.")
    except Exception as e:
        logger.warning("StreakService nicht verfuegbar: %s", e)

    # ------------------------------------------------------------------
    # Sticker-Service  (Datei: sticker_service.py -> class StickerService)
    # ------------------------------------------------------------------
    sticker = None
    try:
        from services.sticker_service import StickerService
        catalog     = str(Path(settings.database_path).parent.parent / "data" / "sticker_catalog.json")
        sticker_dir = str(Path(settings.database_path).parent.parent / "media" / "stickers")
        sticker = StickerService(catalog_path=catalog, sticker_dir=sticker_dir)
        logger.info("StickerService bereit.")
    except Exception as e:
        logger.debug("StickerService nicht verfuegbar: %s", e)

    # ------------------------------------------------------------------
    # Services-Dict — alles was Handler brauchen
    # ------------------------------------------------------------------
    services = {
        "llm":             llm,
        "stt":             stt,           # direkt verfuegbar fuer voice.py
        "tts":             tts,
        "voice_pipeline":  vp,
        "user_repo":       user_repo,
        "memory_repo":     memory_repo,
        "lesson_planner":  lesson_planner,
        "dialogue_router": dialogue_router,
        "streak":          streak,
        "sticker_service": sticker,
    }
    logger.info("Services bereit: %s", list(services.keys()))
    return services


# Alias fuer app/main.py
initialise_services = init_services
