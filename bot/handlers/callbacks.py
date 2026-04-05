"""Handler fuer Inline-Keyboard Callbacks (Help-Buttons, Teacher-Wechsel, Quiz-Antworten)."""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

logger = logging.getLogger(__name__)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # Ladeindikator stoppen

    data = query.data or ""
    services = context.bot_data.get("services", {})
    settings = context.bot_data.get("settings")
    user_repo = services.get("user_repo")

    if not user_repo or not settings:
        await query.edit_message_text("Сервис временно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    # --- Teacher wechseln ---
    if data.startswith("teacher_"):
        teacher_name = data.split("_", 1)[1]
        if teacher_name in {"vitali", "dering", "imperator"}:
            user_repo.set_teacher(user_id, teacher_name)
            labels = {"vitali": "Vitali 😊", "dering": "Dering 📐", "imperator": "Imperator 🔥"}
            await query.edit_message_text(
                f"✅ Учитель изменён: *{labels[teacher_name]}*",
                parse_mode="Markdown",
            )
        return

    # --- Schnellbefehle aus Help ---
    if data == "cmd_lesson":
        # Simuliere /lesson Aufruf
        from bot.handlers.lesson import handle_lesson
        await handle_lesson(update, context)
        return

    if data == "cmd_quiz":
        from bot.handlers.quiz import handle_quiz
        await handle_quiz(update, context)
        return

    if data == "cmd_progress":
        from bot.handlers.progress import handle_progress
        await handle_progress(update, context)
        return

    # --- Quiz Inline-Antworten (1-4 als Buttons) ---
    if data.startswith("quiz_"):
        # Weiterleiten an quiz Handler mit simuliertem Text
        answer = data.split("_", 1)[1]  # "1", "2", "3", "4"
        if update.callback_query.message:
            # Inject answer in user_data und quiz aufrufen
            context.user_data["_quiz_inline_answer"] = answer
            from bot.handlers.quiz import handle_quiz_inline
            await handle_quiz_inline(update, context, answer)
        return

    logger.warning("Unknown callback data: %s", data)
