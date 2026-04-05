"""Handler fuer /setlevel - Sprachlevel setzen."""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

VALID_LEVELS = {"beginner", "a1", "a2", "b1", "b2", "c1"}

LEVEL_LABELS = {
    "beginner": "\U0001f4ab Beginner (selbst definiert)",
    "a1": "\U0001f535 A1 — Grundkenntnisse",
    "a2": "\U0001f7e6 A2 — Grundlegende Kenntnisse",
    "b1": "\U0001f7e2 B1 — Mittlere Kenntnisse",
    "b2": "\U0001f7e1 B2 — Gute Kenntnisse",
    "c1": "\U0001f534 C1 — Fortgeschritten",
}

TEACHER_LEVEL_MSGS = {
    "vitali": {
        "beginner": "\U0001f60a Отлично! Начинаем с основ",
        "a1": "\U0001f535 Хорошо! Уровень A1 — самое важное время!",
        "a2": "\U0001f7e6 A2! Уже есть база!",
        "b1": "\U0001f7e2 B1 — отличный выбор!",
        "b2": "\U0001f7e1 B2! Уважаю — ты уже хорошо говоришь!",
        "c1": "\U0001f525 C1 — почти безупречный!",
    },
    "dering": {
        "beginner": "Уровень: начальный. Начинаем систематично.",
        "a1": "Уровень A1. Обновляем.",
        "a2": "Уровень A2. Записано.",
        "b1": "Уровень B1. Хорошая основа.",
        "b2": "Уровень B2. Серьёзно.",
        "c1": "Уровень C1. Работаем по высшей программе.",
    },
    "imperator": {
        "beginner": "\U0001f4ab Начало. Хорошо.",
        "a1": "A1. Движемся.",
        "a2": "A2. Записано.",
        "b1": "B1. Хорошо.",
        "b2": "B2. Уважаю.",
        "c1": "C1. \U0001f525",
    },
}

HELP_TEXT = (
    "\U0001f4d0 *Выбери свой уровень:*\n\n"
    "/setlevel beginner\n"
    "/setlevel a1\n"
    "/setlevel a2\n"
    "/setlevel b1\n"
    "/setlevel b2\n"
    "/setlevel c1\n"
)


async def handle_setlevel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")

    if not user_repo:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)

    args = context.args
    if not args or args[0].lower() not in VALID_LEVELS:
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
        return

    new_level = args[0].lower()
    user_repo.set_level(user_id, new_level)

    level_label = LEVEL_LABELS[new_level]
    teacher_msg = TEACHER_LEVEL_MSGS.get(teacher, TEACHER_LEVEL_MSGS["vitali"]).get(new_level, "")

    reply = f"*{level_label}*\n{teacher_msg}"
    await update.message.reply_text(reply, parse_mode="Markdown")
