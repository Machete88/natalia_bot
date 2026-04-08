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

    # Quiz-Antworten
    if data.startswith("quiz_"):
        answer = data.split("_", 1)[1]
        await handle_quiz_inline(update, context, answer)
        return

    # Lesson Topic
    if data.startswith("lesson_topic_"):
        topic = data[len("lesson_topic_"):]
        from bot.handlers.lesson import handle_lesson_topic_callback
        await handle_lesson_topic_callback(update, context, topic)
        return

    # Rollenspiele
    if data.startswith("rp_"):
        scenario_key = data[len("rp_"):]
        from bot.handlers.roleplay import handle_rp_callback
        await handle_rp_callback(update, context, scenario_key)
        return

    await query.answer()
    logger.warning("Unbekannter Callback: %s", data)
