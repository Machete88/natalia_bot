"""ElevenLabs TTS provider mit automatischer Russisch/Deutsch-Spracherkennung."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path
import httpx
from .base import BaseTTSProvider

# Erkennt ob ein Token kyrillisch (ru) oder lateinisch/deutsch (de) ist
_CYRILLIC = re.compile(r'[\u0400-\u04FF]')
_GERMAN_CHARS = re.compile(r'[\u00C0-\u024F\u00e4\u00f6\u00fc\u00c4\u00d6\u00dc\u00df]')


def _detect_lang(text: str) -> str:
    """Grobe Spracherkennung: ru wenn Kyrillisch dominiert, sonst de."""
    cyrillic_count = len(_CYRILLIC.findall(text))
    latin_count = len(re.findall(r'[a-zA-Z]', text))
    return "ru" if cyrillic_count >= latin_count else "de"


def _split_by_language(text: str) -> list[tuple[str, str]]:
    """
    Teilt Text in Segmente auf und markiert jedes als 'ru' oder 'de'.
    Beispiel: 'Heute lernen wir das Wort Apfel яблоко'
    -> [('de', 'Heute lernen wir das Wort Apfel '), ('ru', 'яблоко')]
    """
    segments: list[tuple[str, str]] = []
    # Aufteilen an Wortgrenzen
    words = re.split(r'(\s+)', text)
    current_lang = None
    current_chunk = ""

    for word in words:
        if not word.strip():
            current_chunk += word
            continue
        lang = _detect_lang(word)
        if lang != current_lang:
            if current_chunk.strip():
                segments.append((current_lang or lang, current_chunk))
            current_lang = lang
            current_chunk = word
        else:
            current_chunk += word

    if current_chunk.strip():
        segments.append((current_lang or "de", current_chunk))

    return segments


class ElevenLabsProvider(BaseTTSProvider):
    BASE = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str) -> None:
        self._key = api_key
        Path("media/cache").mkdir(parents=True, exist_ok=True)

    async def synthesize(self, text: str, voice: str) -> Path:
        key = hashlib.sha1((voice + text).encode()).hexdigest()
        path = Path("media/cache") / f"el_{key}.mp3"
        if path.exists():
            return path

        # Sprache des Gesamttexts bestimmen
        dominant_lang = _detect_lang(text)

        url = f"{self.BASE}/text-to-speech/{voice}"
        headers = {"xi-api-key": self._key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "language_code": dominant_lang,
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.80,
                "style": 0.20,
                "use_speaker_boost": True,
            },
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            path.write_bytes(resp.content)
        return path
