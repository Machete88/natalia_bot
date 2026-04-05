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

    # STT
    stt_provider_name = (settings.stt_provider or "mock").lower()
    if stt_provider_name == "whisper_local":
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

    router = DialogueRouter(llm_provider=llm, user_repo=user_repo, memory_repo=memory_repo)

    # Mapping Lehrer -> Voice-ID aus .env
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

    return {
        "llm": llm,
        "tts": tts,
        "stt": stt,
        "user_repo": user_repo,
        "memory_repo": memory_repo,
        "dialogue_router": router,
        "voice_pipeline": voice_pipeline,
        "sticker_service": sticker_service,
    }