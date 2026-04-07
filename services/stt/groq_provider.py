"""Groq Whisper STT Provider - kostenlos, cloud-basiert."""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from services.stt.base import BaseSTTProvider

logger = logging.getLogger(__name__)

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


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

            # Dateiendung bestimmen
            suffix = audio_path.suffix.lower().lstrip(".") or "ogg"
            mime = f"audio/{suffix}"

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    GROQ_STT_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    files={
                        "file": (audio_path.name, audio_bytes, mime),
                        "model": (None, self._model),
                        "language": (None, "ru"),
                        "response_format": (None, "json"),
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                text = data.get("text", "").strip()
                logger.info("Groq STT: '%s'", text[:80])
                return text or "[\u0433\u043e\u043b\u043e\u0441 \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043d, \u043d\u043e \u0442\u0435\u043a\u0441\u0442 \u043f\u0443\u0441\u0442\u043e\u0439]"
        except Exception as e:
            logger.error("Groq STT failed: %s", e)
            return ""
