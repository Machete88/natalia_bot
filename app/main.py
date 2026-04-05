"""Entry point fuer natalia_bot."""
from __future__ import annotations

import logging
import sys
from pathlib import Path


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

    settings = Settings.from_env()
    _setup_logging(settings.log_file)
    logger = logging.getLogger(__name__)
    logger.info("natalia_bot starting...")

    from services.runtime_init import initialise_services
    from bot.application import build_application
    from db.database import init_db

    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    init_db(settings.database_path)
    logger.info("Database ready: %s", settings.database_path)

    services = initialise_services(settings)
    logger.info("Services initialised.")

    # Taeglich-Erinnerung aus .env einrichten
    def _setup_reminder(app) -> None:
        try:
            from datetime import time as dtime
            from zoneinfo import ZoneInfo
            import random

            reminder_time_str = settings.daily_reminder_time
            tz_name = settings.timezone
            hour, minute = map(int, reminder_time_str.split(":"))
            tz = ZoneInfo(tz_name)

            from services.reminder import REMINDER_MESSAGES

            async def reminder_job(context) -> None:
                user_repo = services.get("user_repo")
                if not user_repo:
                    return
                tg_id = settings.authorized_user_id
                if not tg_id:
                    return
                uid = user_repo.get_or_create_user(int(tg_id), "")
                teacher = user_repo.get_teacher(uid)
                msgs = REMINDER_MESSAGES.get(teacher, REMINDER_MESSAGES["vitali"])
                msg = random.choice(msgs)
                try:
                    await context.bot.send_message(chat_id=int(tg_id), text=msg)
                except Exception as e:
                    logger.warning("Reminder send failed: %s", e)

            app.job_queue.run_daily(
                reminder_job,
                time=dtime(hour=hour, minute=minute, tzinfo=tz),
                name="daily_reminder",
            )
            logger.info("Daily reminder scheduled at %s (%s)", reminder_time_str, tz_name)
        except Exception as e:
            logger.warning("Could not schedule daily reminder: %s", e)

    app = build_application(settings, services)
    _setup_reminder(app)
    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
