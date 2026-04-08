"""
Script: Telegram Sticker Pack erstellen + file_ids in sticker_catalog.json speichern.

Nutzung:
  cd C:\\natalia_bot
  .venv\\Scripts\\python.exe scripts/upload_stickers.py
"""
from __future__ import annotations
import asyncio, json, os, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
STICKER_DIR  = ROOT / "media" / "stickers"
CATALOG_PATH = ROOT / "data" / "sticker_catalog.json"

# .env automatisch laden
def _load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())

_load_env()

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
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    user_id = int(os.getenv("AUTHORIZED_USER_ID", "0"))

    if not token or not user_id:
        print("Fehler: TELEGRAM_BOT_TOKEN und AUTHORIZED_USER_ID nicht gefunden.")
        print(f"  .env Pfad: {ROOT / '.env'}")
        sys.exit(1)

    from telegram import Bot, InputSticker
    from telegram.constants import StickerFormat

    bot      = Bot(token=token)
    bot_info = await bot.get_me()
    pack_name = f"natalia_lernen_by_{bot_info.username}"

    print(f"Bot: @{bot_info.username}")
    print(f"Pack-Name: {pack_name}")
    print(f"Sticker-Ordner: {STICKER_DIR}")
    print()

    # Verfuegbare Sticker-Dateien sammeln
    available: list[tuple[str, str]] = []  # (filename, event)
    missing:   list[str] = []
    for filename, event in STICKER_MAP.items():
        path = STICKER_DIR / filename
        if path.exists():
            available.append((filename, event))
        else:
            missing.append(filename)

    if missing:
        print(f"Fehlende Dateien ({len(missing)}) — werden uebersprungen:")
        for m in missing:
            print(f"  ⚠️  {m}")
        print()

    if not available:
        print("Keine Sticker-Dateien gefunden!")
        print(f"Bitte PNG-Dateien nach {STICKER_DIR} kopieren.")
        sys.exit(1)

    print(f"Lade {len(available)} Sticker hoch...")

    # InputSticker-Objekte vorbereiten
    sticker_inputs: list[tuple[InputSticker, str]] = []
    for filename, event in available:
        path = STICKER_DIR / filename
        data = path.read_bytes()
        sticker_inputs.append((
            InputSticker(sticker=data, emoji_list=["\U0001f4da"], format=StickerFormat.STATIC),
            event
        ))

    # Pack erstellen (erster Sticker)
    try:
        await bot.create_new_sticker_set(
            user_id   = user_id,
            name      = pack_name,
            title     = "Natalia Lernen",
            stickers  = [sticker_inputs[0][0]],
            sticker_format = StickerFormat.STATIC,
        )
        print("  Pack erstellt!")
    except Exception as e:
        if "already" in str(e).lower():
            print("  Pack existiert bereits — fuege Sticker hinzu.")
        else:
            print(f"  Pack-Erstellung fehlgeschlagen: {e}")
            sys.exit(1)

    # Restliche Sticker hinzufuegen
    for sticker_obj, event in sticker_inputs[1:]:
        try:
            await bot.add_sticker_to_set(
                user_id = user_id,
                name    = pack_name,
                sticker = sticker_obj,
            )
            print(f"  + {event}")
        except Exception as e:
            print(f"  Fehler bei {event}: {e}")

    # file_ids aus dem Pack lesen
    pack = await bot.get_sticker_set(pack_name)
    print(f"\nPack hat {len(pack.stickers)} Sticker.")

    # Catalog aufbauen: event -> [file_id, ...]
    catalog: dict[str, list[str]] = {k: [] for k in STICKER_MAP.values()}
    event_list = [ev for _, ev in sticker_inputs]
    for i, sticker in enumerate(pack.stickers):
        if i < len(event_list):
            catalog[event_list[i]].append(sticker.file_id)
            print(f"  {event_list[i]:12s} -> {sticker.file_id[:40]}...")

    # Catalog speichern
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\n\u2705 Catalog gespeichert: {CATALOG_PATH}")
    print(f"\U0001f4e6 Pack URL: https://t.me/addstickers/{pack_name}")


if __name__ == "__main__":
    asyncio.run(main())
