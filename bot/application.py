"""Build and configure the Telegram Application."""
from __future__ import annotations
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config.settings import Settings

logger = logging.getLogger(__name__)


async def build_application(settings: Settings, services: dict) -> Application:
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["services"] = services
    app.bot_data["settings"] = settings

    allowed = {settings.authorized_user_id, settings.admin_user_id}
    auth_filter = filters.User(user_id=list(allowed))

    from bot.handlers.start import handle_start
    from bot.handlers.help import handle_help
    from bot.handlers.messages import handle_text
    from bot.handlers.voice import handle_voice
    from bot.handlers.lesson import handle_lesson
    from bot.handlers.teacher import handle_teacher
    from bot.handlers.progress import handle_progress
    from bot.handlers.stats import handle_stats
    from bot.handlers.homework import handle_homework
    from bot.handlers.setlevel import handle_setlevel
    from bot.handlers.quiz import handle_quiz
    from bot.handlers.pronunciation import handle_pronounce
    from bot.handlers.remind import handle_remind
    from bot.handlers.support import deactivate_support
    from bot.handlers.callbacks import handle_callback

    # Commands
    app.add_handler(CommandHandler("start",      handle_start,       filters=auth_filter))
    app.add_handler(CommandHandler("help",       handle_help,        filters=auth_filter))
    app.add_handler(CommandHandler("lesson",     handle_lesson,      filters=auth_filter))
    app.add_handler(CommandHandler("teacher",    handle_teacher,     filters=auth_filter))
    app.add_handler(CommandHandler("progress",   handle_progress,    filters=auth_filter))
    app.add_handler(CommandHandler("stats",      handle_stats,       filters=auth_filter))
    app.add_handler(CommandHandler("setlevel",   handle_setlevel,    filters=auth_filter))
    app.add_handler(CommandHandler("quiz",       handle_quiz,        filters=auth_filter))
    app.add_handler(CommandHandler("pronounce",  handle_pronounce,   filters=auth_filter))
    app.add_handler(CommandHandler("remind",     handle_remind,      filters=auth_filter))
    app.add_handler(CommandHandler("endsupport", deactivate_support, filters=auth_filter))

    # Inline-Keyboard Callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Messages
    app.add_handler(MessageHandler(auth_filter & filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(auth_filter & filters.VOICE,        handle_voice))
    app.add_handler(MessageHandler(auth_filter & filters.PHOTO,        handle_homework))
    app.add_handler(MessageHandler(auth_filter & filters.Document.ALL, handle_homework))

    try:
        _schedule_user_reminders(app, settings)
    except Exception as e:
        logger.warning("Could not schedule reminders: %s", e)

    logger.info("Handlers registered. Authorized users: %s", allowed)
    return app


def _schedule_user_reminders(app: Application, settings: Settings) -> None:
    import sqlite3
    from datetime import time as dtime
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(settings.timezone)
    except Exception:
        tz = None

    try:
        with sqlite3.connect(settings.database_path) as conn:
            rows = conn.execute(
                "SELECT telegram_id, remind_time FROM reminders WHERE active=1"
            ).fetchall()
    except Exception as e:
        logger.warning("Could not load user reminders: %s", e)
        return

    import random
    from services.reminder import REMINDER_MESSAGES

    for telegram_id, remind_time in rows:
        try:
            hour, minute = map(int, remind_time.split(":"))
            chat_id = int(telegram_id)

            async def _job(context, _chat_id=chat_id) -> None:
                svc = context.bot_data.get("services", {})
                user_repo = svc.get("user_repo")
                teacher = "vitali"
                if user_repo:
                    uid = user_repo.get_or_create_user(_chat_id, "")
                    teacher = user_repo.get_teacher(uid)
                msgs = REMINDER_MESSAGES.get(teacher, REMINDER_MESSAGES["vitali"])
                try:
                    await context.bot.send_message(chat_id=_chat_id, text=random.choice(msgs))
                except Exception as e:
                    logger.warning("User reminder failed for %s: %s", _chat_id, e)

            app.job_queue.run_daily(
                _job,
                time=dtime(hour=hour, minute=minute, tzinfo=tz),
                name=f"user_reminder_{telegram_id}",
            )
        except Exception as e:
            logger.warning("Could not schedule reminder for %s: %s", telegram_id, e)
