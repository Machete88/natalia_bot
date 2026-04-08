"""ElevenLabs TTS Provider — robuste Implementierung.

Verbesserungen:
- Markdown/Emoji Bereinigung vor API-Call
- Text-Chunking fuer lange Nachrichten (>2500 Zeichen)
- Exponentielles Retry (3x) bei 5xx / Timeout
- Spracherkennung (ru/de) per Segment fuer gemischten Text
- Modell: eleven_turbo_v2_5 (schnell, guenstig, mehrsprachig)
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from pathlib import Path

import httpx

from .base import BaseTTSProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Spracherkennung
# ---------------------------------------------------------------------------
_CYRILLIC = re.compile(r'[\u0400-\u04FF]')


def _detect_lang(text: str) -> str:
    """Gibt 'ru' zurueck wenn Kyrillisch dominiert, sonst 'de'."""
    cyrillic = len(_CYRILLIC.findall(text))
    latin    = len(re.findall(r'[a-zA-Z]', text))
    return "ru" if cyrillic > latin else "de"


# ---------------------------------------------------------------------------
# Text-Bereinigung
# ---------------------------------------------------------------------------
_MARKDOWN_RE = re.compile(
    r'```.*?```'        # Code-Bloecke
    r'|`[^`]+`'         # Inline-Code
    r'|\*{1,3}([^*]+)\*{1,3}'  # Bold/Italic
    r'|_{1,3}([^_]+)_{1,3}'    # Underscore Bold/Italic
    r'|~{2}([^~]+)~{2}'        # Strikethrough
    r'|\[([^\]]+)\]\([^)]+\)', # Markdown-Links
    re.DOTALL
)
# Telegram-Sonderzeichen die als Markdown durchkommen
_TELEGRAM_ESCAPE = re.compile(r'[\\`*_{\[\]()#.!>|+=\-]')
# Emoji-Ranges
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\u2600-\u27BF"
    "\ufe0f\u20e3\u200d"
    "]+"
)
_MULTI_SPACE = re.compile(r'  +')
_MULTI_NL    = re.compile(r'\n{3,}')

_MAX_CHUNK = 2400  # ElevenLabs empfohlenes Limit pro Request


def _clean_for_tts(text: str) -> str:
    """Entfernt Markdown, Emojis und ueberfluessige Formatierung fuer TTS."""
    # Code-Bloecke: erhalten nur den Inhalt
    text = re.sub(r'```(?:\w+)?\n?(.*?)```', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Fett/Kursiv aufloesen
    text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_\n]+)_{1,3}', r'\1', text)
    text = re.sub(r'~{2}([^~]+)~{2}', r'\1', text)
    # Links: nur Linktext
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Emojis entfernen
    text = _EMOJI_RE.sub('', text)
    # Telegram-Escape-Zeichen
    text = re.sub(r'\\([!.`*_{}\[\]()#+\-=|<>])', r'\1', text)
    # Ueberfluessige Leerzeichen / Zeilenumbrueche
    text = _MULTI_NL.sub('\n\n', text)
    text = _MULTI_SPACE.sub(' ', text)
    return text.strip()


def _chunk_text(text: str, max_len: int = _MAX_CHUNK) -> list[str]:
    """Teilt langen Text an Satzgrenzen auf."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    # Aufteilen an Satz-Grenzen: . ! ?
    sentences = re.split(r'(?<=[.!?\n])\s+', text)
    current   = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_len:
            current = (current + " " + sent).strip() if current else sent
        else:
            if current:
                chunks.append(current)
            # Satz selbst zu lang? Hart aufteilen.
            if len(sent) > max_len:
                for i in range(0, len(sent), max_len):
                    chunks.append(sent[i:i + max_len])
                current = ""
            else:
                current = sent
    if current:
        chunks.append(current)
    return chunks


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class ElevenLabsProvider(BaseTTSProvider):
    """Async ElevenLabs TTS mit Retry, Chunking und Text-Cleanup."""

    BASE = "https://api.elevenlabs.io/v1"
    _RETRY_DELAYS = (1.0, 3.0, 7.0)  # exponentielles Retry

    def __init__(self, api_key: str, cache_dir: str = "media/cache") -> None:
        self._key   = api_key
        self._cache = Path(cache_dir)
        self._cache.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, text: str, voice: str) -> Path:
        key = hashlib.sha1((voice + text).encode()).hexdigest()
        return self._cache / f"el_{key}.ogg"

    async def synthesize(self, text: str, voice: str) -> Path:
        """Haupteintrittspunkt. Gibt Pfad zur .ogg-Datei zurueck."""
        clean = _clean_for_tts(text)
        if not clean:
            logger.warning("TTS: Text nach Bereinigung leer.")
            clean = text[:200]  # Fallback: roh

        # Cache-Check auf bereinigten Text
        path = self._cache_path(clean, voice)
        if path.exists() and path.stat().st_size > 100:
            logger.debug("TTS-Cache HIT: %s", path.name)
            return path

        chunks = _chunk_text(clean)
        if len(chunks) == 1:
            await self._synthesize_chunk(chunks[0], voice, path)
        else:
            # Mehrere Chunks -> einzeln synthetisieren und zusammenfuehren
            logger.info("TTS: Text aufgeteilt in %d Chunks", len(chunks))
            parts: list[Path] = []
            for i, chunk in enumerate(chunks):
                part_path = self._cache / f"el_{path.stem}_part{i}.ogg"
                if not (part_path.exists() and part_path.stat().st_size > 100):
                    await self._synthesize_chunk(chunk, voice, part_path)
                parts.append(part_path)
            _concat_ogg(parts, path)

        return path

    async def _synthesize_chunk(self, text: str, voice: str, out: Path) -> None:
        """Sendet einen Chunk an ElevenLabs mit exponentiellem Retry."""
        lang    = _detect_lang(text)
        url     = f"{self.BASE}/text-to-speech/{voice}"
        headers = {"xi-api-key": self._key, "Content-Type": "application/json"}
        payload = {
            "text":     text,
            "model_id": "eleven_turbo_v2_5",
            "language_code": lang,
            "output_format": "ogg_48000",
            "voice_settings": {
                "stability":        0.45,
                "similarity_boost": 0.80,
                "style":            0.20,
                "use_speaker_boost": True,
            },
        }

        last_exc: Exception | None = None
        for attempt, delay in enumerate(self._RETRY_DELAYS, 1):
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 429:
                        # Rate-Limit: warten und erneut versuchen
                        retry_after = float(resp.headers.get("Retry-After", delay * 2))
                        logger.warning("TTS Rate-Limit. Warte %.1fs", retry_after)
                        await asyncio.sleep(retry_after)
                        continue
                    resp.raise_for_status()
                    out.write_bytes(resp.content)
                    logger.debug("TTS OK: %d Bytes -> %s", len(resp.content), out.name)
                    return
            except (httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
                last_exc = exc
                logger.warning("TTS Versuch %d/%d fehlgeschlagen: %s", attempt, len(self._RETRY_DELAYS), exc)
                if attempt < len(self._RETRY_DELAYS):
                    await asyncio.sleep(delay)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    raise  # 4xx nicht wiederholen
                last_exc = exc
                logger.warning("TTS HTTP %d bei Versuch %d", exc.response.status_code, attempt)
                if attempt < len(self._RETRY_DELAYS):
                    await asyncio.sleep(delay)

        raise RuntimeError(f"TTS nach {len(self._RETRY_DELAYS)} Versuchen fehlgeschlagen") from last_exc


def _concat_ogg(parts: list[Path], out: Path) -> None:
    """Verbindet mehrere .ogg Dateien naiv durch binaeres Aneinanderhaengen.
    Fuer Telegram-Voice-Nachrichten ausreichend; fuer professionelle
    Nutzung wuerde man ffmpeg verwenden.
    """
    with out.open("wb") as f:
        for p in parts:
            if p.exists():
                f.write(p.read_bytes())
