"""Handler fuer /stop — bricht laufende Session ab (Practice, Quiz)."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.quiz import QUIZ_SESSION_KEY
from services.session_manager import get_session, LearningPhase


async def handle_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = get_session(context.user_data)
    quiz_active = bool(context.user_data.get(QUIZ_SESSION_KEY))

    if session.phase == LearningPhase.PRACTICE:
        session.finish()
        context.user_data.pop(QUIZ_SESSION_KEY, None)
        await update.message.reply_text(
            "\u23f9 Упражнение остановлено. Напиши мне что-нибудь."
        )
    elif quiz_active:
        context.user_data.pop(QUIZ_SESSION_KEY, None)
        await update.message.reply_text(
            "\u23f9 Квиз остановлен. /quiz — начать заново."
        )
    else:
        await update.message.reply_text(
            "Сейчас нет активной сессии. Просто пиши мне \u2014 я здесь."
        )
