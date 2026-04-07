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


MOTIVATION = [
    "Weitermachen.",
    "Woerter sind Macht.",
    "Fortschritt. Weiter.",
]

PROGRESS_TEMPLATE = (
    "\U0001f525 *Zahlen:*\n\n"
    "Neu: *{new}* | Lernt: *{learning}* | Fertig: *{mastered}*\n"
    "Streak: *{current_streak}* Tage. Rekord: *{longest_streak}*\n\n"
    "{motivation}"
)


async def handle_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    settings = context.bot_data.get("settings")

    if not user_repo or not settings:
        await update.message.reply_text("Service vorueber gehend nicht verfuegbar.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    stats = _get_vocab_stats(settings.database_path, user_id)
    motivation = MOTIVATION[stats["mastered"] % len(MOTIVATION)]

    msg = PROGRESS_TEMPLATE.format(motivation=motivation, **stats)
    await update.message.reply_text(msg, parse_mode="Markdown")
