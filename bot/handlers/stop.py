"""Handler fuer /stop."""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.session_manager import get_session, LearningPhase

logger = logging.getLogger(__name__)


async def handle_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = get_session(context.user_data)
    if session.phase == LearningPhase.IDLE:
        await update.message.reply_text("Нечего останавливать.")
        return
    session.finish()
    await update.message.reply_text("✅ Остановлено.")
