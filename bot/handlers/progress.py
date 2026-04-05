"""Handler fuer /progress Befehl - Lernfortschritt anzeigen."""
from __future__ import annotations

import logging
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def _get_vocab_stats(db_path: str, user_id: int) -> dict:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT status, COUNT(*) as cnt
            FROM vocab_progress
            WHERE user_id = ?
            GROUP BY status
            """,
            (user_id,),
        ).fetchall()
        stats = {"new": 0, "learning": 0, "mastered": 0}
        for row in rows:
            stats[row["status"]] = row["cnt"]

        total_vocab = conn.execute("SELECT COUNT(*) as cnt FROM vocab_items").fetchone()["cnt"]
        total_seen = sum(stats.values())
        return {**stats, "total_vocab": total_vocab, "total_seen": total_seen}


PROGRESS_TEMPLATES = {
    "vitali": (
        "\U0001f4ca *Твой прогресс, Наташа!* \U0001f60a\n\n"
        "\u2728 Новые (ещё не видела): *{new}*\n"
        "\U0001f504 В процессе (учишь): *{learning}*\n"
        "\U0001f3c6 Выучила: *{mastered}*\n\n"
        "Всего слов в базе: *{total_vocab}*\n"
        "Слов начато: *{total_seen}*\n\n"
        "{motivation}"
    ),
    "dering": (
        "\U0001f4cb *Статус обучения:*\n\n"
        "Не начато: *{new}*\n"
        "В работе: *{learning}*\n"
        "Освоено: *{mastered}*\n\n"
        "Всего единиц: *{total_vocab}* | Начато: *{total_seen}*"
    ),
    "imperator": (
        "\U0001f525 *Цифры:*\n\n"
        "Новых: *{new}* | Учишь: *{learning}* | Готово: *{mastered}*\n"
        "База: *{total_vocab}* слов. Начато: *{total_seen}*.\n\n"
        "{motivation}"
    ),
}

MOTIVATION = {
    "vitali": [
        "Ты молодец! Продолжай в том же духе \U0001f4aa",
        "Каждое слово — шаг вперёд. Я горжусь тобой! \U0001f31f",
        "Так держать! Немецкий покорится! \U0001f1e9\U0001f1ea",
    ],
    "imperator": [
        "Двигайся дальше.",
        "Слова — это сила. Собирай их.",
        "Прогресс есть. Продолжай.",
    ],
}


def _pick_motivation(teacher: str, mastered: int) -> str:
    msgs = MOTIVATION.get(teacher, [])
    if not msgs:
        return ""
    return msgs[mastered % len(msgs)]


async def handle_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    settings = context.bot_data.get("settings")

    if not user_repo or not settings:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)

    stats = _get_vocab_stats(settings.database_path, user_id)
    motivation = _pick_motivation(teacher, stats["mastered"])

    template = PROGRESS_TEMPLATES.get(teacher, PROGRESS_TEMPLATES["vitali"])
    msg = template.format(motivation=motivation, **stats)

    await update.message.reply_text(msg, parse_mode="Markdown")
