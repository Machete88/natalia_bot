"""Taeglich geplante Lern-Erinnerungen."""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

REMINDER_MSGS = {
    "vitali": [
        "\U0001f31e Доброе утро, Наташа! Сегодня ещё не учили. У нас есть 5 новых слов — /lesson \U0001f60a",
        "\U0001f4da Наташа! Каждый день немножко — это уже очень много. Начнём? /lesson",
        "\U0001f1e9\U0001f1ea Германия ждёт! Сегодня ещё 5 слов и /quiz — и ты будешь чуть ближе \U0001f60a",
    ],
    "dering": [
        "\U0001f4cb Сегодня ещё нет записи о прохождении занятия. /lesson",
        "\u23f0 Время учиться. /lesson или /quiz",
        "Урок ожидает. /lesson",
    ],
    "imperator": [
        "\U0001f525 Сегодня пока нет занятия. /lesson",
        "\U0001f525 /quiz. Слова ждут.",
        "\U0001f525 Немецкий не учит себя сам. /lesson",
    ],
}

STREAK_MSGS = {
    "vitali": {
        3:  "\U0001f525 3 дня подряд! Ты на верном пути, Наташа!",
        7:  "\U0001f38a Неделя без перерыва! Я такими горжусь \U0001f60a",
        14: "\U0001f3c6 2 недели! Это уже настоящая привычка!",
        30: "\U0001f947 Месяц каждый день! Наташа, ты просто фантастическая!",
    },
    "dering": {
        3:  "3-дневная серия. Продолжай.",
        7:  "7 дней. Хорошо.",
        14: "14 дней. Серьёзный подход.",
        30: "30 дней. Уважаю.",
    },
    "imperator": {
        3:  "\U0001f525 3. Продолжай.",
        7:  "\U0001f525 7. Хорошо.",
        14: "\U0001f525 14. Сильно.",
        30: "\U0001f947 30. Император доволен.",
    },
}


def get_or_create_streak(db_path: str, user_id: int) -> int:
    """Gibt aktuellen Streak zurueck (Tage in Folge gelernt)."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT value FROM user_preferences WHERE user_id=? AND key='streak'",
            (user_id,),
        ).fetchone()
        return int(row["value"]) if row else 0


def update_streak(db_path: str, user_id: int) -> int:
    """Aktualisiert den Streak nach einer Lern-Session. Gibt neuen Streak zurueck."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # Letzter Lern-Tag
        row = conn.execute(
            "SELECT value FROM user_preferences WHERE user_id=? AND key='last_learned'",
            (user_id,),
        ).fetchone()

        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        streak_row = conn.execute(
            "SELECT value FROM user_preferences WHERE user_id=? AND key='streak'",
            (user_id,),
        ).fetchone()
        current_streak = int(streak_row["value"]) if streak_row else 0

        if row:
            last_date = row["value"]
            if last_date == today:
                return current_streak  # Heute schon gezaehlt
            elif last_date == yesterday:
                new_streak = current_streak + 1
            else:
                new_streak = 1  # Luecke -> Reset
        else:
            new_streak = 1

        conn.execute(
            "INSERT OR REPLACE INTO user_preferences (user_id, key, value) VALUES (?,?,?)",
            (user_id, "last_learned", today),
        )
        conn.execute(
            "INSERT OR REPLACE INTO user_preferences (user_id, key, value) VALUES (?,?,?)",
            (user_id, "streak", str(new_streak)),
        )
        return new_streak


async def send_daily_reminder(
    bot,
    db_path: str,
    telegram_id: int,
    user_id: int,
    teacher: str,
) -> None:
    """Sendet taeglich eine Erinnerung falls der Nutzer heute noch nicht gelernt hat."""
    import random
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT value FROM user_preferences WHERE user_id=? AND key='last_learned'",
            (user_id,),
        ).fetchone()
        today = datetime.now().strftime("%Y-%m-%d")
        if row and row["value"] == today:
            return  # Heute schon gelernt

    msgs = REMINDER_MSGS.get(teacher, REMINDER_MSGS["vitali"])
    msg = random.choice(msgs)

    streak = get_or_create_streak(db_path, user_id)
    if streak > 0:
        streak_note = f"\n\U0001f525 Серия: {streak} дней подряд!"
        msg = msg + streak_note

    try:
        await bot.send_message(chat_id=telegram_id, text=msg)
    except Exception as e:
        logger.warning("Reminder send failed for %s: %s", telegram_id, e)
