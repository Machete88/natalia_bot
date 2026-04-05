"""Build and configure the Telegram Application."""
from __future__ import annotations
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
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
    from bot.handlers.messages import handle_text
    from bot.handlers.voice import handle_voice
    from bot.handlers.lesson import handle_lesson
    from bot.handlers.teacher import handle_teacher
    from bot.handlers.progress import handle_progress
    from bot.handlers.homework import handle_homework

    # Befehle
    app.add_handler(CommandHandler("start", handle_start, filters=auth_filter))
    app.add_handler(CommandHandler("lesson", handle_lesson, filters=auth_filter))
    app.add_handler(CommandHandler("teacher", handle_teacher, filters=auth_filter))
    app.add_handler(CommandHandler("progress", handle_progress, filters=auth_filter))

    # Nachrichten
    app.add_handler(MessageHandler(auth_filter & filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(auth_filter & filters.VOICE, handle_voice))

    # Hausaufgaben: Foto oder Dokument
    app.add_handler(MessageHandler(auth_filter & filters.PHOTO, handle_homework))
    app.add_handler(MessageHandler(auth_filter & filters.Document.ALL, handle_homework))

    logger.info("Handlers registered. Authorized users: %s", allowed)
    return app
