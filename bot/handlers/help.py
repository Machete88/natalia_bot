"""Handler fuer /help Befehl."""
from __future__ import annotations

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

HELP_TEXT = """
🤖 *Natalia Bot — Команды*

📚 *Учёба:*
/lesson — 5 новых слов
/lesson еда — слова по теме
/quiz — викторина с выбором ответа
/pronounce слово — произношение

📊 *Прогресс:*
/progress — твой прогресс и стрик
/stats — подробная статистика по темам

👨‍🏫 *Учителя:*
/teacher vitali — тёплый и весёлый
/teacher dering — строгий и точный
/teacher imperator — холодный и загадочный

⚙️ *Настройки:*
/setlevel a1 — установить уровень (a1-c1)
/remind 09:00 — ежедневное напоминание

💬 *Просто пиши текст* — свободный разговор с учителем
🎤 *Голосовое сообщение* — расшифровка + ответ
📷 *Фото/файл* — проверка домашней работы

🗣 *Темы для уроков:*
еда, цвета, числа, время, семья, тело,
путешествия, работа, дом, погода,
покупки, чувства, животные
"""


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("📚 Урок", callback_data="cmd_lesson"),
            InlineKeyboardButton("🧩 Викторина", callback_data="cmd_quiz"),
            InlineKeyboardButton("📊 Прогресс", callback_data="cmd_progress"),
        ],
        [
            InlineKeyboardButton("👨‍🏫 Vitali", callback_data="teacher_vitali"),
            InlineKeyboardButton("📐 Dering", callback_data="teacher_dering"),
            InlineKeyboardButton("🔥 Imperator", callback_data="teacher_imperator"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        HELP_TEXT,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )
