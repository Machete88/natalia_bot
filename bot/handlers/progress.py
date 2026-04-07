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
            if row["status"] in stats:
                stats[row["status"]] = row["cnt"]

        total_vocab = conn.execute("SELECT COUNT(*) as cnt FROM vocab_items").fetchone()["cnt"]
        total_seen = sum(stats.values())

        # Streak - defensiv: Tabelle koennte im Test-DB fehlen
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
            # Tabelle existiert nicht - ignorieren
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
        "\U0001f4ca *\u0422\u0432\u043e\u0439 \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441, \u041d\u0430\u0442\u0430\u0448\u0430!* \U0001f60a\n\n"
        "\u2728 \u041d\u043e\u0432\u044b\u0435: *{new}*\n"
        "\U0001f504 \u0423\u0447\u0438\u0448\u044c: *{learning}*\n"
        "\U0001f3c6 \u0412\u044b\u0443\u0447\u0438\u043b\u0430: *{mastered}*\n\n"
        "\u0412\u0441\u0435\u0433\u043e \u0441\u043b\u043e\u0432: *{total_vocab}* | \u041d\u0430\u0447\u0430\u0442\u043e: *{total_seen}*\n\n"
        "\U0001f525 \u0421\u0442\u0440\u0438\u043a: *{current_streak}* \u0434\u043d\u0435\u0439 | \u0420\u0435\u043a\u043e\u0440\u0434: *{longest_streak}*\n\n"
        "{motivation}"
    ),
    "dering": (
        "\U0001f4cb *\u0421\u0442\u0430\u0442\u0443\u0441:*\n\n"
        "\u041d\u0435 \u043d\u0430\u0447\u0430\u0442\u043e: *{new}* | \u0412 \u0440\u0430\u0431\u043e\u0442\u0435: *{learning}* | \u041e\u0441\u0432\u043e\u0435\u043d\u043e: *{mastered}*\n"
        "\u0412\u0441\u0435\u0433\u043e: *{total_vocab}* \u0441\u043b\u043e\u0432. | \u041d\u0430\u0447\u0430\u0442\u043e: *{total_seen}*\n"
        "\U0001f525 \u0421\u0442\u0440\u0438\u043a: *{current_streak}* / \u0420\u0435\u043a\u043e\u0440\u0434: *{longest_streak}*"
    ),
    "imperator": (
        "\U0001f525 *\u0426\u0438\u0444\u0440\u044b:*\n\n"
        "\u041d\u043e\u0432\u044b\u0445: *{new}* | \u0423\u0447\u0438\u0448\u044c: *{learning}* | \u0413\u043e\u0442\u043e\u0432\u043e: *{mastered}*\n"
        "\u0421\u0442\u0440\u0438\u043a: *{current_streak}* \u0434\u043d. \u0420\u0435\u043a\u043e\u0440\u0434: *{longest_streak}*\n\n"
        "{motivation}"
    ),
}

MOTIVATION = {
    "vitali": [
        "\u0422\u044b \u043c\u043e\u043b\u043e\u0434\u0435\u0446! \u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0430\u0439 \U0001f4aa",
        "\u041a\u0430\u0436\u0434\u043e\u0435 \u0441\u043b\u043e\u0432\u043e \u2014 \u0448\u0430\u0433 \u0432\u043f\u0435\u0440\u0451\u0434! \U0001f31f",
        "\u0422\u0430\u043a \u0434\u0435\u0440\u0436\u0430\u0442\u044c! \U0001f1e9\U0001f1ea",
    ],
    "imperator": [
        "\u0414\u0432\u0438\u0433\u0430\u0439\u0441\u044f \u0434\u0430\u043b\u044c\u0448\u0435.",
        "\u0421\u043b\u043e\u0432\u0430 \u2014 \u044d\u0442\u043e \u0441\u0438\u043b\u0430.",
        "\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u0435\u0441\u0442\u044c. \u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0430\u0439.",
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
        await update.message.reply_text("\u0421\u0435\u0440\u0432\u0438\u0441 \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)

    stats = _get_vocab_stats(settings.database_path, user_id)
    motivation = _pick_motivation(teacher, stats["mastered"])

    template = PROGRESS_TEMPLATES.get(teacher, PROGRESS_TEMPLATES["vitali"])
    msg = template.format(motivation=motivation, **stats)

    await update.message.reply_text(msg, parse_mode="Markdown")
