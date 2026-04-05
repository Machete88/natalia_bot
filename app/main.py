"""Entry point fuer natalia_bot."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Windows asyncio Policy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _setup_logging(log_file: str = "logs/bot.log") -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def main() -> None:
    from config.settings import Settings

    settings = Settings()
    _setup_logging(settings.log_file)
    logger = logging.getLogger(__name__)
    logger.info("natalia_bot starting...")

    from services.runtime_init import initialise_services
    from bot.application import build_application
    from db.database import init_db

    # DB initialisieren
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    init_db(settings.database_path)
    logger.info("Database ready: %s", settings.database_path)

    services = initialise_services(settings)
    logger.info("Services initialised.")

    async def run() -> None:
        app = await build_application(settings, services)

        # Taeglich-Erinnerung einrichten
        try:
            from datetime import time as dtime
            import pytz
            from telegram.ext import JobQueue
            from services.reminder import send_daily_reminder

            reminder_time_str = services.get("reminder_time", "09:00")
            tz_name = services.get("timezone", "Europe/Berlin")
            hour, minute = map(int, reminder_time_str.split(":"))
            tz = pytz.timezone(tz_name)

            async def reminder_job(context) -> None:
                user_repo = services.get("user_repo")
                db_path = settings.database_path
                if not user_repo:
                    return
                # Alle autorisierten User
                for tg_id in [settings.authorized_user_id]:
                    if not tg_id:
                        continue
                    uid = user_repo.get_or_create_user(int(tg_id), "")
                    teacher = user_repo.get_teacher(uid)
                    await send_daily_reminder(
                        bot=context.bot,
                        db_path=db_path,
                        telegram_id=int(tg_id),
                        user_id=uid,
                        teacher=teacher,
                    )

            app.job_queue.run_daily(
                reminder_job,
                time=dtime(hour=hour, minute=minute, tzinfo=tz),
                name="daily_reminder",
            )
            logger.info("Daily reminder scheduled at %s (%s)", reminder_time_str, tz_name)
        except Exception as e:
            logger.warning("Could not schedule daily reminder: %s", e)

        logger.info("Bot is running. Press Ctrl+C to stop.")
        await app.run_polling(drop_pending_updates=True)

    asyncio.run(run())


if __name__ == "__main__":
    main()
