"""
Sticker Service — sendet passende Sticker basierend auf Event-Typ.

Events:
  greeting, correct, wrong, close, fire, praise, thinking,
  lesson, quiz, progress, streak, reminder, nika, family, done
"""
from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from telegram import Bot

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).parent.parent / "data" / "sticker_catalog.json"
_catalog: dict[str, list[str]] | None = None


def _load_catalog() -> dict[str, list[str]]:
    global _catalog
    if _catalog is None:
        try:
            _catalog = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Sticker-Catalog nicht geladen: %s", e)
            _catalog = {}
    return _catalog


async def send_sticker(bot: Bot, chat_id: int, event: str) -> bool:
    """
    Sendet einen zufaelligen Sticker fuer das gegebene Event.
    Gibt True zurueck wenn erfolgreich, sonst False.
    """
    catalog = _load_catalog()
    file_ids = catalog.get(event, [])
    if not file_ids:
        logger.debug("Kein Sticker fuer Event '%s'", event)
        return False
    file_id = random.choice(file_ids)
    try:
        await bot.send_sticker(chat_id=chat_id, sticker=file_id)
        logger.debug("Sticker gesendet: event=%s", event)
        return True
    except Exception as e:
        logger.warning("Sticker senden fehlgeschlagen (%s): %s", event, e)
        return False


# Convenience-Aliases
async def sticker_correct(bot: Bot, chat_id: int)  -> bool: return await send_sticker(bot, chat_id, "correct")
async def sticker_wrong(bot: Bot, chat_id: int)    -> bool: return await send_sticker(bot, chat_id, "wrong")
async def sticker_praise(bot: Bot, chat_id: int)   -> bool: return await send_sticker(bot, chat_id, "praise")
async def sticker_greeting(bot: Bot, chat_id: int) -> bool: return await send_sticker(bot, chat_id, "greeting")
async def sticker_done(bot: Bot, chat_id: int)     -> bool: return await send_sticker(bot, chat_id, "done")
async def sticker_streak(bot: Bot, chat_id: int)   -> bool: return await send_sticker(bot, chat_id, "streak")
async def sticker_fire(bot: Bot, chat_id: int)     -> bool: return await send_sticker(bot, chat_id, "fire")
