"""Handler fuer /progress Befehl - Lernfortschritt inkl. Streak."""
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

        # Streak - defensiv: Tabelle koennte fehlen
        current_streak = 0
        longest_streak = 0
        try:
            streak_row = conn.execute(
                "SELECT current_streak, longest_streak FROM streaks WHERE user_id=?",
                (user_id,),
            ).fetchone()
            if streak_row:
                current_streak = streak_row["current_streak"]
                longest_streak = streak_row["longest_streak"]
        except sqlite3.OperationalError:
            pass

        return {
            **stats,
            "total_vocab": total_vocab,
            "total_seen": total_seen,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
        }


PROGRESS_TEMPLATES = {
    "vitali": (
        "\U0001f4ca *Твой прогресс, Наташа!* \U0001f60a\n\n"
        "\u2728 Новые: *{new}*\n"
        "\U0001f504 Учишь: *{learning}*\n"
        "\U0001f3c6 Выучила: *{mastered}*\n\n"
        "Всего слов: *{total_vocab}* | Начато: *{total_seen}*\n\n"
        "\U0001f525 Стрик: *{current_streak}* дней | Рекорд: *{longest_streak}*\n\n"
        "{motivation}"
    ),
    "dering": (
        "\U0001f4cb *Статус:*\n\n"
        "Не начато: *{new}* | В работе: *{learning}* | Освоено: *{mastered}*\n"
        "Всего: *{total_vocab}* слов. | Начато: *{total_seen}*\n"
        "\U0001f525 Стрик: *{current_streak}* / Рекорд: *{longest_streak}*"
    ),
    "imperator": (
        "\U0001f525 *Цифры:*\n\n"
        "Новых: *{new}* | Учишь: *{learning}* | Готово: *{mastered}*\n"
        "Стрик: *{current_streak}* дн. Рекорд: *{longest_streak}*\n\n"
        "{motivation}"
    ),
}

MOTIVATION = {
    "vitali": [
        "Ты молодец! Продолжай \U0001f4aa",
        "Каждое слово — шаг вперёд! \U0001f31f",
        "Так держать! \U0001f1e9\U0001f1ea",
    ],
    "imperator": [
        "Двигайся дальше.",
        "Слова — это сила.",
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
