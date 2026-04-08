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


async def api(token: str, method: str, **kwargs) -> dict:
    """Ruft die Telegram Bot API direkt per httpx auf."""
    import httpx
    url = f"https://api.telegram.org/bot{token}/{method}"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, **kwargs)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"{method} fehlgeschlagen: {data.get('description')}")
    return data["result"]


async def main():
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    user_id = int(os.getenv("AUTHORIZED_USER_ID", "0"))

    if not token or not user_id:
        print("Fehler: TELEGRAM_BOT_TOKEN und AUTHORIZED_USER_ID nicht gefunden.")
        sys.exit(1)

    bot_info  = await api(token, "getMe")
    pack_name = f"natalia_lernen_by_{bot_info['username']}"

    print(f"Bot:          @{bot_info['username']}")
    print(f"Pack-Name:    {pack_name}")
    print(f"Sticker-Ordner: {STICKER_DIR}")
    print()

    # Dateien pruefen
    available: list[tuple[Path, str]] = []
    for filename, event in STICKER_MAP.items():
        path = STICKER_DIR / filename
        if path.exists():
            available.append((path, event))
        else:
            print(f"  Nicht gefunden: {filename}")

    if not available:
        print(f"\nKeine Sticker unter {STICKER_DIR} — bitte PNGs zuerst generieren.")
        sys.exit(1)

    print(f"Lade {len(available)} Sticker hoch...\n")

    # --- Pack erstellen (erster Sticker) ---
    first_path, first_event = available[0]
    try:
        with open(first_path, "rb") as f:
            await api(token, "createNewStickerSet",
                data={
                    "user_id":        user_id,
                    "name":           pack_name,
                    "title":          "Natalia Lernen",
                    "sticker_type":   "regular",
                    "stickers":       json.dumps([{
                        "sticker":     "attach://sticker0",
                        "emoji_list":  ["\U0001f4da"],
                        "format":      "static",
                    }]),
                },
                files={"sticker0": (first_path.name, f, "image/png")},
            )
        print(f"  Pack erstellt! (erster Sticker: {first_event})")
    except RuntimeError as e:
        if "already" in str(e).lower():
            print("  Pack existiert bereits.")
        else:
            print(f"  {e}")
            sys.exit(1)

    # --- Weitere Sticker hinzufuegen ---
    for i, (path, event) in enumerate(available[1:], start=1):
        try:
            with open(path, "rb") as f:
                await api(token, "addStickerToSet",
                    data={
                        "user_id": user_id,
                        "name":    pack_name,
                        "sticker": json.dumps({
                            "sticker":    f"attach://sticker{i}",
                            "emoji_list": ["\U0001f4da"],
                            "format":     "static",
                        }),
                    },
                    files={f"sticker{i}": (path.name, f, "image/png")},
                )
            print(f"  + {event}")
        except RuntimeError as e:
            print(f"  Fehler bei {event}: {e}")

    # --- file_ids lesen ---
    pack = await api(token, "getStickerSet", params={"name": pack_name})
    stickers = pack["stickers"]
    print(f"\nPack hat {len(stickers)} Sticker.\n")

    catalog: dict[str, list[str]] = {k: [] for k in STICKER_MAP.values()}
    event_order = [ev for _, ev in available]
    for i, sticker in enumerate(stickers):
        if i < len(event_order):
            fid = sticker["file_id"]
            catalog[event_order[i]].append(fid)
            print(f"  {event_order[i]:12s} -> {fid[:45]}...")

    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\n\u2705 Catalog gespeichert: {CATALOG_PATH}")
    print(f"\U0001f4e6 Pack:  https://t.me/addstickers/{pack_name}")


if __name__ == "__main__":
    asyncio.run(main())
