"""Zentrale Callback-Query-Verarbeitung."""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.quiz import handle_quiz_inline

logger = logging.getLogger(__name__)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    data = query.data or ""
    logger.debug("Callback: %s", data)

    # Quiz-Antworten: quiz_1 … quiz_4
    if data.startswith("quiz_"):
        answer = data.split("_", 1)[1]
        await handle_quiz_inline(update, context, answer)
        return

    # Lesson Topic-Auswahl: lesson_topic_<topic|all>
    if data.startswith("lesson_topic_"):
        topic = data[len("lesson_topic_"):]
        from bot.handlers.lesson import handle_lesson_topic_callback
        await handle_lesson_topic_callback(update, context, topic)
        return

    # Unbekannter Callback
    await query.answer()
    logger.warning("Unbekannter Callback: %s", data)
