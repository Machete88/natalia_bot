"""
Script: Telegram Sticker Pack erstellen + file_ids in sticker_catalog.json speichern.

Nutzung:
  1. Bot starten
  2. python scripts/upload_stickers.py
  3. Folge den Anweisungen
"""
from __future__ import annotations
import asyncio, json, os, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
STICKER_DIR  = ROOT / "media" / "stickers"
CATALOG_PATH = ROOT / "data" / "sticker_catalog.json"

# Sticker-Definition: filename -> event-key
STICKER_MAP = {
    "s_start.png":    "greeting",
    "s_correct.png":  "correct",
    "s_wrong.png":    "wrong",
    "s_close.png":    "close",
    "s_fire.png":     "fire",
    "s_trophy.png":   "praise",
    "s_think.png":    "thinking",
    "s_lesson.png":   "lesson",
    "s_quiz.png":     "quiz",
    "s_progress.png": "progress",
    "s_streak.png":   "streak",
    "s_reminder.png": "reminder",
    "s_nika.png":     "nika",
    "s_family.png":   "family",
    "s_done.png":     "done",
}


async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    user_id = int(os.getenv("AUTHORIZED_USER_ID", "0"))
    if not token or not user_id:
        print("Fehler: TELEGRAM_BOT_TOKEN und AUTHORIZED_USER_ID in .env benoetigt.")
        sys.exit(1)

    from telegram import Bot, InputSticker
    from telegram.constants import StickerFormat

    bot = Bot(token=token)
    catalog: dict[str, list[str]] = {k: [] for k in set(STICKER_MAP.values())}

    print(f"Lade {len(STICKER_MAP)} Sticker hoch...")
    sticker_files = []

    for filename, event in STICKER_MAP.items():
        path = STICKER_DIR / filename
        if not path.exists():
            print(f"  Datei fehlt: {path}")
            continue

        with open(path, "rb") as f:
            sticker_files.append(InputSticker(
                sticker=f.read(),
                emoji_list=["📚"],
                format=StickerFormat.STATIC,
            ))

    # Pack erstellen
    pack_name = f"natalia_lernen_by_{(await bot.get_me()).username}"
    print(f"Pack-Name: {pack_name}")

    try:
        await bot.create_new_sticker_set(
            user_id=user_id,
            name=pack_name,
            title="Natalia Lernen",
            stickers=sticker_files[:1],  # Erst einen hochladen
            sticker_format=StickerFormat.STATIC,
        )
        print("  Pack erstellt!")
    except Exception as e:
        if "already exists" not in str(e).lower():
            print(f"  Pack-Erstellung fehlgeschlagen: {e}")

    # Alle weiteren hinzufuegen + file_ids sammeln
    pack = await bot.get_sticker_set(pack_name)
    for sticker in pack.stickers:
        print(f"  file_id: {sticker.file_id}")

    # Catalog speichern
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print(f"\nCatalog gespeichert: {CATALOG_PATH}")
    print(f"Pack URL: https://t.me/addstickers/{pack_name}")


if __name__ == "__main__":
    asyncio.run(main())
