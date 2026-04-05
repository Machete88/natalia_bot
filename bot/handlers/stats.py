"""Handler fuer /stats Befehl - detaillierte Statistik nach Themen."""
from __future__ import annotations

import logging
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

TOPIC_NAMES = {
    "food": "🍕 Еда",
    "colors": "🎨 Цвета",
    "numbers": "🔢 Числа",
    "time": "⏰ Время",
    "family": "👨‍👩‍👧 Семья",
    "body": "🦷 Тело",
    "travel": "✈️ Путешествия",
    "work": "💼 Работа",
    "home": "🏠 Дом",
    "weather": "🌤 Погода",
    "shopping": "🛍 Покупки",
    "feelings": "💭 Чувства",
    "animals": "🐾 Животные",
    "general": "📚 Общие",
}


def _get_topic_stats(db_path: str, user_id: int) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                vi.topic,
                COUNT(vi.id) as total,
                SUM(CASE WHEN vp.status = 'mastered' THEN 1 ELSE 0 END) as mastered,
                SUM(CASE WHEN vp.status = 'learning' THEN 1 ELSE 0 END) as learning,
                SUM(CASE WHEN vp.status IS NULL OR vp.status = 'new' THEN 1 ELSE 0 END) as new_count
            FROM vocab_items vi
            LEFT JOIN vocab_progress vp ON vi.id = vp.vocab_id AND vp.user_id = ?
            GROUP BY vi.topic
            ORDER BY mastered DESC, total DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _get_quiz_stats(db_path: str, user_id: int) -> dict:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT COUNT(*) as total_seen,
                   SUM(CASE WHEN status = 'mastered' THEN 1 ELSE 0 END) as mastered,
                   SUM(CASE WHEN status = 'learning' THEN 1 ELSE 0 END) as learning
            FROM vocab_progress WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        streak_row = conn.execute(
            "SELECT current_streak, longest_streak FROM streaks WHERE user_id=?",
            (user_id,),
        ).fetchone()
        return {
            "total_seen": row["total_seen"] or 0,
            "mastered": row["mastered"] or 0,
            "learning": row["learning"] or 0,
            "current_streak": streak_row["current_streak"] if streak_row else 0,
            "longest_streak": streak_row["longest_streak"] if streak_row else 0,
        }


def _progress_bar(done: int, total: int, width: int = 8) -> str:
    if total == 0:
        return "░" * width
    filled = round((done / total) * width)
    return "█" * filled + "░" * (width - filled)


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    settings = context.bot_data.get("settings")

    if not user_repo or not settings:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)
    level = user_repo.get_level(user_id)

    topic_rows = _get_topic_stats(settings.database_path, user_id)
    overall = _get_quiz_stats(settings.database_path, user_id)

    lines = [
        f"📊 *Подробная статистика*",
        f"Уровень: *{level.upper()}* | Учитель: *{teacher.capitalize()}*",
        f"🔥 Стрик: *{overall['current_streak']}* дн. | Рекорд: *{overall['longest_streak']}* дн.",
        "",
        f"📚 *По темам:*",
    ]

    for row in topic_rows:
        topic = row.get("topic") or "general"
        label = TOPIC_NAMES.get(topic, f"📦 {topic.capitalize()}")
        total = row["total"]
        mastered = row["mastered"] or 0
        learning = row["learning"] or 0
        bar = _progress_bar(mastered, total)
        pct = int((mastered / total * 100)) if total else 0
        lines.append(
            f"{label}\n"
            f"  {bar} {mastered}/{total} ({pct}%) | 🔄 {learning}"
        )

    lines += [
        "",
        f"✅ Всего выучено: *{overall['mastered']}* слов",
        f"🔄 В процессе: *{overall['learning']}*",
        f"👀 Всего встречено: *{overall['total_seen']}*",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
