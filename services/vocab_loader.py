"""Laed Vokabeln aus JSON-Seed-Datei in die Datenbank."""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SEED_PATH = Path("content/vocab_seed.json")


def load_vocab_seed(db_path: str, seed_path: Path = DEFAULT_SEED_PATH) -> int:
    """Laed Vokabeln aus der Seed-Datei, wenn die Tabelle noch leer ist.

    Gibt die Anzahl der eingefuegten Eintraege zurueck.
    """
    if not seed_path.exists():
        logger.warning("Vocab seed file not found: %s", seed_path)
        return 0

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM vocab_items").fetchone()[0]
        if count > 0:
            logger.info("Vocab seed already loaded (%d items), skipping.", count)
            return 0

        with open(seed_path, encoding="utf-8") as f:
            items = json.load(f)

        conn.executemany(
            """
            INSERT INTO vocab_items (level, topic, word_de, word_ru, example_de, example_ru)
            VALUES (:level, :topic, :word_de, :word_ru, :example_de, :example_ru)
            """,
            items,
        )
        logger.info("Loaded %d vocab items from seed.", len(items))
        return len(items)
