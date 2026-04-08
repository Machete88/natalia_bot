"""Handler fuer /stats — detaillierte Statistik nach Themen + SM-2 Vorschau."""
from __future__ import annotations

import logging
import sqlite3
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

TOPIC_NAMES = {
    "food":     "\U0001f355 Еда",
    "colors":   "\U0001f3a8 Цвета",
    "numbers":  "\U0001f522 Числа",
    "time":     "\u23f0 Время",
    "family":   "\U0001f46a Семья",
    "body":     "\U0001f9b7 Тело",
    "travel":   "\u2708️ Путешествия",
    "work":     "\U0001f4bc Работа",
    "home":     "\U0001f3e0 Дом",
    "weather":  "\U0001f324 Погода",
    "shopping": "\U0001f6cd Покупки",
    "feelings": "\U0001f4ad Чувства",
    "animals":  "\U0001f43e Животные",
    "general":  "\U0001f4da Общие",
}


def _get_topic_stats(db_path: str, user_id: int) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                vi.topic,
                COUNT(vi.id)  AS total,
                SUM(CASE WHEN vp.status = 'mastered' THEN 1 ELSE 0 END) AS mastered,
                SUM(CASE WHEN vp.status = 'learning' THEN 1 ELSE 0 END) AS learning
            FROM vocab_items vi
            LEFT JOIN vocab_progress vp ON vi.id = vp.vocab_id AND vp.user_id = ?
            GROUP BY vi.topic
            ORDER BY mastered DESC, total DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _get_overall(db_path: str, user_id: int) -> dict:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT COUNT(*) AS total_seen,
                   SUM(CASE WHEN status='mastered' THEN 1 ELSE 0 END) AS mastered,
                   SUM(CASE WHEN status='learning' THEN 1 ELSE 0 END) AS learning
            FROM vocab_progress WHERE user_id=?
            """,
            (user_id,),
        ).fetchone()

        streak_row = conn.execute(
            "SELECT current_streak, longest_streak FROM streaks WHERE user_id=?",
            (user_id,),
        ).fetchone()

        # SM-2: faellige Wiederholungen heute
        due_today = conn.execute(
            """
            SELECT COUNT(*) FROM vocab_progress
            WHERE user_id=?
              AND next_review_date IS NOT NULL
              AND next_review_date <= ?
              AND status != 'mastered'
            """,
            (user_id, date.today().isoformat()),
        ).fetchone()[0] or 0

        return {
            "total_seen":      row["total_seen"]  or 0,
            "mastered":        row["mastered"]    or 0,
            "learning":        row["learning"]    or 0,
            "current_streak":  streak_row["current_streak"]  if streak_row else 0,
            "longest_streak":  streak_row["longest_streak"] if streak_row else 0,
            "due_today":       due_today,
        }


def _bar(done: int, total: int, width: int = 8) -> str:
    if total == 0:
        return "\u2591" * width
    filled = round((done / total) * width)
    return "\u2588" * filled + "\u2591" * (width - filled)


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services  = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    settings  = context.bot_data.get("settings")

    if not user_repo or not settings:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user    = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    level   = user_repo.get_level(user_id)

    topic_rows = _get_topic_stats(settings.database_path, user_id)
    overall    = _get_overall(settings.database_path, user_id)

    streak_emoji = "\U0001f525" if overall["current_streak"] >= 7 else "\U0001f4aa"

    lines = [
        "\U0001f4ca *Подробная статистика*",
        f"Уровень: *{level.upper()}*",
        f"{streak_emoji} Стрик: *{overall['current_streak']}* дн. | Рекорд: *{overall['longest_streak']}* дн.",
    ]

    if overall["due_today"] > 0:
        lines.append(f"\u23f0 Сегодня на повторение: *{overall['due_today']}* слов \u2014 /lesson")

    lines += ["", "\U0001f4da *По темам:*"]

    for row in topic_rows:
        topic   = row.get("topic") or "general"
        label   = TOPIC_NAMES.get(topic, f"\U0001f4e6 {topic.capitalize()}")
        total   = row["total"]
        mastered= row["mastered"] or 0
        learning= row["learning"] or 0
        bar     = _bar(mastered, total)
        pct     = int(mastered / total * 100) if total else 0
        lines.append(f"{label}\n  {bar} {mastered}/{total} ({pct}%) | \U0001f504 {learning}")

    lines += [
        "",
        f"\u2705 Выучено: *{overall['mastered']}* слов",
        f"\U0001f504 В процессе: *{overall['learning']}*",
        f"\U0001f440 Всего встречено: *{overall['total_seen']}*",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
