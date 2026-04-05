"""Sticker service with catalog-based selection."""
from __future__ import annotations
import json, random, logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class StickerService:
    def __init__(self, catalog_path: str, sticker_dir: str) -> None:
        self._catalog: dict = {}
        self._dir = Path(sticker_dir)
        try:
            self._catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Sticker catalog not loaded: %s", e)

    def get_sticker_for_event(self, event: str) -> Optional[str]:
        stickers = self._catalog.get(event, [])
        return random.choice(stickers) if stickers else None

    def maybe_send_sticker(self, event: str, probability: float = 0.5) -> Optional[str]:
        if random.random() < probability:
            return self.get_sticker_for_event(event)
        return None

    def choose_contextual_sticker(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if any(w in text_lower for w in ["привет", "здравствуй", "добрый"]):
            return self.get_sticker_for_event("greeting")
        if any(w in text_lower for w in ["молодец", "отлично", "браво", "хорошо"]):
            return self.get_sticker_for_event("praise")
        if any(w in text_lower for w in ["ника", "собак", "щенок"]):
            return self.get_sticker_for_event("nika")
        if any(w in text_lower for w in ["настя", "анастасия", "дочь"]):
            return self.get_sticker_for_event("family")
        return None
