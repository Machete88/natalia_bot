"""Tests fuer TTSCache."""
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from services.tts_cache import TTSCache


class FakeTTS:
    def __init__(self, output_path: Path):
        self._path = output_path
        self.call_count = 0

    async def synthesize(self, text: str, voice_id: str) -> Path:
        self.call_count += 1
        self._path.write_bytes(b"fake_audio")
        return self._path


def test_cache_hit_avoids_second_call():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        audio_out = Path(tmp) / "out.ogg"
        fake = FakeTTS(audio_out)
        cache = TTSCache(fake, cache_dir=str(cache_dir))

        async def run():
            r1 = await cache.synthesize("Hallo", "voice1")
            r2 = await cache.synthesize("Hallo", "voice1")
            return r1, r2

        r1, r2 = asyncio.run(run())
        assert fake.call_count == 1  # zweiter Call nutzt Cache
        assert r1.name == r2.name


def test_different_texts_both_called():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        audio_out = Path(tmp) / "out.ogg"
        fake = FakeTTS(audio_out)
        cache = TTSCache(fake, cache_dir=str(cache_dir))

        async def run():
            await cache.synthesize("Hallo", "voice1")
            await cache.synthesize("Tschüss", "voice1")

        asyncio.run(run())
        assert fake.call_count == 2


def test_clear_cache():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        audio_out = Path(tmp) / "out.ogg"
        fake = FakeTTS(audio_out)
        cache = TTSCache(fake, cache_dir=str(cache_dir))

        asyncio.run(cache.synthesize("Test", "v"))
        assert cache.cache_size() == 1
        deleted = cache.clear_cache()
        assert deleted == 1
        assert cache.cache_size() == 0
