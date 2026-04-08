"""TTS package — exportiert BaseTTSProvider und Factory."""
from .base import BaseTTSProvider


def create_tts_provider(settings) -> BaseTTSProvider | None:
    """Erstellt den konfigurierten TTS-Provider. Gibt None bei Fehler zurueck."""
    import logging
    logger = logging.getLogger(__name__)

    if getattr(settings, "tts_provider", "") == "elevenlabs":
        try:
            from .elevenlabs_provider import ElevenLabsProvider
            provider = ElevenLabsProvider(
                api_key   = settings.elevenlabs_api_key,
                cache_dir = getattr(settings, "audio_cache_dir", "media/cache"),
            )
            logger.info("TTS: ElevenLabsProvider bereit")
            return provider
        except Exception as e:
            logger.error("TTS ElevenLabs Initialisierung fehlgeschlagen: %s", e)

    # Mock-Fallback (kein Audio, kein Crash)
    try:
        from .mock_provider import MockTTSProvider
        logger.warning("TTS: MockProvider aktiv — kein Audio")
        return MockTTSProvider()
    except Exception:
        return None


__all__ = ["BaseTTSProvider", "create_tts_provider"]
