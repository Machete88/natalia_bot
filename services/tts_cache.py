"""TTS-Cache: synthetisierte Audio-Dateien per Hash cachen.

Verhindert wiederholte ElevenLabs-API-Calls fuer identische Texte.
Cache-Key: md5(text + voice_id) → .ogg Datei in AUDIO_CACHE_DIR.
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TTSCache:
    """Wrapper um einen TTS-Provider der gecachte Ergebnisse zurueckgibt."""

    def __init__(self, tts_provider, cache_dir: str = "media/cache") -> None:
        self._tts   = tts_provider
        self._cache = Path(cache_dir)
        self._cache.mkdir(parents=True, exist_ok=True)
        logger.info("TTS-Cache aktiv: %s", self._cache)

    def _cache_path(self, text: str, voice_id: str) -> Path:
        key = hashlib.md5(f"{voice_id}:{text}".encode()).hexdigest()
        return self._cache / f"{key}.ogg"

    async def synthesize(self, text: str, voice_id: str) -> Path:
        """Gibt gecachten Pfad zurueck oder ruft TTS-Provider auf."""
        path = self._cache_path(text, voice_id)
        if path.exists() and path.stat().st_size > 0:
            logger.debug("TTS-Cache HIT: %s", path.name)
            return path

        logger.debug("TTS-Cache MISS — synthetisiere: %.40s…", text)
        result = await self._tts.synthesize(text, voice_id)

        # Ergebnis in Cache kopieren wenn es nicht schon dort liegt
        result_path = Path(result)
        if result_path.resolve() != path.resolve():
            import shutil
            shutil.copy2(result_path, path)

        return path

    def cache_size(self) -> int:
        """Anzahl gecachter Dateien."""
        return sum(1 for _ in self._cache.glob("*.ogg"))

    def clear_cache(self) -> int:
        """Loescht alle Cache-Dateien. Gibt Anzahl geloeschter Dateien zurueck."""
        count = 0
        for f in self._cache.glob("*.ogg"):
            f.unlink(missing_ok=True)
            count += 1
        logger.info("TTS-Cache geleert: %d Dateien geloescht", count)
        return count

    # Proxy alle anderen Attribute an den echten Provider
    def __getattr__(self, name: str):
        return getattr(self._tts, name)
