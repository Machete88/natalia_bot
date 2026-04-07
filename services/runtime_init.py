"""Initialise all services based on settings."""
from __future__ import annotations
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def initialise_services(settings) -> Dict[str, Any]:
    from db.repositories.user_repository import UserRepository
    from db.repositories.memory_repository import MemoryRepository
    from services.dialogue_router import DialogueRouter
    from services.voice_pipeline import VoicePipeline
    from services.sticker_service import StickerService
    from services.lesson_planner import LessonPlanner
    from services.vocab_loader import load_vocab_seed

    # LLM
    llm_provider_name = (settings.llm_provider or "mock").lower()
    if llm_provider_name == "openai" and settings.openai_api_key:
        from services.llm import OpenAIProvider
        llm = OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or "https://openrouter.ai/api/v1",
            model=settings.llm_model,
        )
        logger.info("LLM: OpenAIProvider (%s)", settings.llm_model)
    else:
        from services.llm import MockLLMProvider
        llm = MockLLMProvider()
        logger.info("LLM: MockLLMProvider")

    # TTS
    tts_provider_name = (settings.tts_provider or "mock").lower()
    if tts_provider_name == "elevenlabs" and settings.elevenlabs_api_key:
        try:
            from services.tts import ElevenLabsProvider
            tts = ElevenLabsProvider(api_key=settings.elevenlabs_api_key)
            logger.info("TTS: ElevenLabsProvider")
        except Exception as e:
            from services.tts import MockTTSProvider
            tts = MockTTSProvider()
            logger.warning("TTS fallback to mock: %s", e)
    else:
        from services.tts import MockTTSProvider
        tts = MockTTSProvider()
        logger.info("TTS: MockTTSProvider")

    # STT - Groq (bevorzugt), dann Whisper lokal, dann Mock
    stt_provider_name = (settings.stt_provider or "mock").lower()
    groq_key = getattr(settings, "groq_api_key", None)

    if groq_key and stt_provider_name in ("groq", "whisper_local", "auto"):
        try:
            from services.stt.groq_provider import GroqSTTProvider
            stt = GroqSTTProvider(api_key=groq_key)
            logger.info("STT: GroqSTTProvider (whisper-large-v3-turbo)")
        except Exception as e:
            from services.stt import MockSTTProvider
            stt = MockSTTProvider()
            logger.warning("STT fallback to mock: %s", e)
    elif stt_provider_name == "whisper_local":
        try:
            from services.stt.whisper_provider import WhisperProvider
            stt = WhisperProvider(model=settings.whisper_model)
            logger.info("STT: WhisperProvider (%s)", settings.whisper_model)
        except Exception as e:
            from services.stt import MockSTTProvider
            stt = MockSTTProvider()
            logger.warning("STT fallback to mock: %s", e)
    else:
        from services.stt import MockSTTProvider
        stt = MockSTTProvider()
        logger.info("STT: MockSTTProvider")

    # Repositories
    user_repo = UserRepository(settings.database_path)
    memory_repo = MemoryRepository(settings.database_path)

    # Lesson planner
    lesson_planner = LessonPlanner(settings.database_path)

    # Vocab-Seed einmalig laden
    try:
        loaded = load_vocab_seed(settings.database_path)
        if loaded:
            logger.info("Vocab seed loaded: %d items.", loaded)
    except Exception as e:
        logger.warning("Vocab seed loading failed: %s", e)

    router = DialogueRouter(llm_provider=llm, user_repo=user_repo, memory_repo=memory_repo)

    voice_map = {
        "vitali": settings.voice_id_vitali,
        "dering": settings.voice_id_dering,
        "imperator": settings.voice_id_imperator,
    }
    voice_pipeline = VoicePipeline(stt=stt, tts=tts, voice_map=voice_map)

    sticker_service = StickerService(
        catalog_path="media/stickers/catalog.json",
        sticker_dir="media/stickers",
    )

    reminder_time = getattr(settings, "daily_reminder_time", "09:00")
    timezone = getattr(settings, "timezone", "Europe/Berlin")

    return {
        "llm": llm,
        "tts": tts,
        "stt": stt,
        "user_repo": user_repo,
        "memory_repo": memory_repo,
        "dialogue_router": router,
        "voice_pipeline": voice_pipeline,
        "sticker_service": sticker_service,
        "lesson_planner": lesson_planner,
        "reminder_time": reminder_time,
        "timezone": timezone,
    }
