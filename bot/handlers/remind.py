"""Handler fuer /remind - Erinnerungen setzen und entfernen."""
from __future__ import annotations

import logging
import re
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

TIME_RE = re.compile(r'^([01]?\d|2[0-3]):([0-5]\d)$')

TEACHER_SET = {
    "vitali": "\U0001f514 Отлично! Буду напоминать тебя каждый день в *{time}*! Учиться каждый день — это ключ к успеху! \U0001f60a",
    "dering": "\U0001f514 Ежедневное напоминание записано: *{time}*.",
    "imperator": "\U0001f514 *{time}*. Ежедневно. Без исключений.",
}

TEACHER_OFF = {
    "vitali": "\U0001f515 Поняла! Напоминание отключено. Но не забывай — я всегда здесь! \U0001f60a",
    "dering": "\U0001f515 Напоминание отключено.",
    "imperator": "\U0001f515 Отключено.",
}

HELP_TEXT = (
    "\U0001f514 *Ежедневное напоминание:*\n\n"
    "/remind 09:00 \u2014 напоминать каждый день в 9:00\n"
    "/remind off \u2014 отключить\n"
)


def _set_reminder(db_path: str, user_id: int, telegram_id: int, remind_time: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO reminders (user_id, telegram_id, remind_time, active) VALUES (?,?,?,1)",
            (user_id, telegram_id, remind_time),
        )


def _disable_reminder(db_path: str, user_id: int) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE reminders SET active=0 WHERE user_id=?", (user_id,))


async def handle_remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    settings = context.bot_data.get("settings")
    user_repo = services.get("user_repo")

    if not user_repo or not settings:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)
    args = context.args

    if not args:
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
        return

    arg = args[0].lower()

    if arg == "off":
        _disable_reminder(settings.database_path, user_id)
        msg = TEACHER_OFF.get(teacher, TEACHER_OFF["vitali"])
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    if TIME_RE.match(arg):
        _set_reminder(settings.database_path, user_id, user.id, arg)
        msg = TEACHER_SET.get(teacher, TEACHER_SET["vitali"]).format(time=arg)
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
