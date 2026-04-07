from __future__ import annotations
from pathlib import Path

from services.stt.base import BaseSTTProvider
import whisper

# Sprachen die der Bot erwartet (Russisch + Deutsch)
_ALLOWED_LANGS = {"ru", "de"}
_FALLBACK_LANG = "ru"


class WhisperProvider(BaseSTTProvider):
    def __init__(self, model: str = "small") -> None:
        self._model_name = model
        self._model = whisper.load_model(model)

    async def transcribe(self, audio_path: Path) -> str:
        # Schritt 1: Sprache automatisch erkennen
        audio = whisper.load_audio(str(audio_path))
        audio_pad = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio_pad).to(self._model.device)
        _, probs = self._model.detect_language(mel)

        # Wahrscheinlichkeiten fuer ru und de
        prob_ru = probs.get("ru", 0.0)
        prob_de = probs.get("de", 0.0)

        # Nur ru oder de erlaubt — nimm die wahrscheinlichere
        if prob_de > prob_ru:
            detected = "de"
        else:
            detected = "ru"

        # Schritt 2: Transkribieren mit erkannter Sprache
        result = self._model.transcribe(str(audio_path), language=detected)
        text = result.get("text", "").strip()
        return text or "[голос распознан, но текст пустой]"
