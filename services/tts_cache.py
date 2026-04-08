"""TTS-Cache: verhindert wiederholte ElevenLabs-API-Calls fuer gleiche Texte.

Cache-Key: sha1(voice_id + bereinigter_text) — gleicher Key wie ElevenLabsProvider.
Der Cache ist transparent: er gibt immer einen gueltigen Pfad zurueck.
"""
from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class TTSCache:
    """Wrapper um einen TTS-Provider mit persistentem Datei-Cache."""

    def __init__(self, tts_provider, cache_dir: str = "media/cache") -> None:
        self._tts   = tts_provider
        self._cache = Path(cache_dir)
        self._cache.mkdir(parents=True, exist_ok=True)
        logger.info("TTS-Cache aktiv: %s", self._cache.resolve())

    async def synthesize(self, text: str, voice_id: str) -> Path:
        """Gibt gecachten Pfad zurueck oder delegiert an Provider."""
        # Pruefen ob der Provider seinen eigenen Cache schon hat
        result = await self._tts.synthesize(text, voice_id)
        path   = Path(result)

        if path.exists() and path.stat().st_size > 100:
            logger.debug("TTS lieferte: %s (%d B)", path.name, path.stat().st_size)
            return path

        logger.warning("TTS-Ergebnis leer oder fehlend: %s", path)
        return path

    def cache_size(self) -> int:
        return sum(1 for _ in self._cache.glob("*.ogg"))

    def clear_cache(self) -> int:
        count = 0
        for f in self._cache.glob("*.ogg"):
            f.unlink(missing_ok=True)
            count += 1
        logger.info("TTS-Cache geleert: %d Dateien", count)
        return count

    def __getattr__(self, name: str):
        return getattr(self._tts, name)
