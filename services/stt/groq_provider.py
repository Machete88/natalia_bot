"""Groq Whisper STT Provider — auto language detection (de + ru mixed)."""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from services.stt.base import BaseSTTProvider

logger = logging.getLogger(__name__)

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Groq Whisper: prompt hint improves mixed-language transcription accuracy.
# We explicitly mention both languages so the model doesn't force-fit to one.
_PROMPT_HINT = (
    "Natasha lernt Deutsch. Sie spricht Russisch und Deutsch gemischt. "
    "Наташа учит немецкий язык. Она говорит по-русски и по-немецки."
)


class GroqSTTProvider(BaseSTTProvider):
    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo") -> None:
        self._api_key = api_key
        self._model = model

    async def transcribe(self, audio_path: Path) -> str:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            logger.warning("Audio file not found: %s", audio_path)
            return ""

        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            suffix = audio_path.suffix.lower().lstrip(".") or "ogg"
            mime = f"audio/{suffix}"

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    GROQ_STT_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    files={
                        "file": (audio_path.name, audio_bytes, mime),
                        "model": (None, self._model),
                        # NO language= field → Whisper auto-detects de/ru/mixed
                        "prompt": (None, _PROMPT_HINT),
                        "response_format": (None, "json"),
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                text = data.get("text", "").strip()
                logger.info("Groq STT: '%s'", text[:80])
                return text or "[голос распознан, но текст пустой]"
        except Exception as e:
            logger.error("Groq STT failed: %s", e)
            return ""
