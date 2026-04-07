"""Local Whisper STT Provider — auto language detection."""
from __future__ import annotations

import logging
from pathlib import Path

from services.stt.base import BaseSTTProvider

logger = logging.getLogger(__name__)

_PROMPT_HINT = (
    "Natasha lernt Deutsch. Sie spricht Russisch und Deutsch gemischt. "
    "Наташа учит немецкий язык. Она говорит по-русски и по-немецки."
)


class WhisperLocalProvider(BaseSTTProvider):
    def __init__(self, model_size: str = "small") -> None:
        self._model_size = model_size
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                import whisper
                self._model = whisper.load_model(self._model_size)
                logger.info("Whisper model '%s' loaded.", self._model_size)
            except ImportError:
                logger.error("openai-whisper not installed. Run: pip install openai-whisper")
                raise

    async def transcribe(self, audio_path: Path) -> str:
        self._load_model()
        try:
            result = self._model.transcribe(
                str(audio_path),
                # No language= → auto-detect de/ru
                initial_prompt=_PROMPT_HINT,
                fp16=False,
            )
            text = (result.get("text") or "").strip()
            detected = result.get("language", "?")
            logger.info("Whisper STT [%s]: '%s'", detected, text[:80])
            return text or "[голос распознан, но текст пустой]"
        except Exception as e:
            logger.error("Whisper transcription failed: %s", e)
            return ""
