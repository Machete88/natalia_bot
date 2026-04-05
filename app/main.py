"""Entry point: python -m app.main"""
from __future__ import annotations
import asyncio, logging, sys
from pathlib import Path

from bot.application import build_application
from config.settings import Settings
from db.database import initialise_database
from services.logger import configure_logging
from services.runtime_init import initialise_services


async def _build(settings, services):
    return await build_application(settings, services)


def main() -> None:
    for d in ["data", "logs", "media/audio", "media/cache", "media/stickers"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    settings = Settings.from_env()
    initialise_database(settings.database_path)
    configure_logging(settings.log_file)
    services = initialise_services(settings)

    app = asyncio.run(_build(settings, services))

    try:
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")


if __name__ == "__main__":
    main()
