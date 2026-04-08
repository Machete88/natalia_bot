"""Handler fuer /help — Herr Imperator erteilt Befehle."""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = """
\U0001f525 *Господин Император объясняет один раз:*

*Основные команды:*
/lesson — получить задание (новые слова)
/quiz — проверка памяти
/progress — твой рапорт
/setlevel — сообщить уровень

*Дополнительно:*
/remind — напоминания о занятиях
/stop — прекратить напоминания

*Разговор:*
Просто пиши — Господин Император ответит.
Голосовое — отправь, я оценю произношение.

_Вопросов нет. Выполняй._
"""


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
