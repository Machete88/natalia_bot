"""ElevenLabs TTS provider."""
from __future__ import annotations
import hashlib
from pathlib import Path
import httpx
from .base import BaseTTSProvider


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
        url = f"{self.BASE}/text-to-speech/{voice}"
        headers = {"xi-api-key": self._key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            path.write_bytes(resp.content)
        return path
