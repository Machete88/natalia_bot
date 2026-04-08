"""Einstiegspunkt fuer den Bot.

Start:
    .venv\\Scripts\\python.exe -m bot.main
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Sicherstellen dass Root-Dir im sys.path ist
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings
from db.database import init_db
from services.runtime_init import init_services
from bot.application import build_application


def _setup_logging(log_file: str) -> None:
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_path), encoding="utf-8"),
        ],
    )


async def main() -> None:
    settings = Settings.from_env()
    _setup_logging(settings.log_file)
    logger = logging.getLogger(__name__)
    logger.info("=== Natalia Bot startet ===")

    # Datenbank-Verzeichnis + Schema anlegen
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    init_db(settings.database_path)
    logger.info("Datenbank bereit: %s", settings.database_path)

    services = init_services(settings)
    logger.info("Services bereit.")

    app = await build_application(settings, services)

    logger.info("Bot laeuft. Druecke Ctrl+C zum Beenden.")
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        # Warten bis Ctrl+C
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
