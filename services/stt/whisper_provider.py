from __future__ import annotations
from pathlib import Path

from services.stt.base import BaseSTTProvider
import whisper


class WhisperProvider(BaseSTTProvider):
    def __init__(self, model: str = "small") -> None:
        # Modell einmalig laden (kann beim ersten Start ein paar Sekunden dauern)
        self._model_name = model
        self._model = whisper.load_model(model)

    async def transcribe(self, audio_path: Path) -> str:
        # Whisper ist synchron, das ist hier okay
        result = self._model.transcribe(str(audio_path), language="ru")
        text = result.get("text", "").strip()
        return text or "[голос распознан, но текст пустой]"