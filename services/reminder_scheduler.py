"""Hintergrund-Scheduler: sendet taeglich Erinnerungen."""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

BERLIN = ZoneInfo("Europe/Berlin")

TEACHER_REMIND_MSGS = {
    "vitali": [
        "\U0001f31e Доброе утро, Наташа! Сегодня отличный день, чтобы поучить немецкий! А начинаем? \U0001f1e9\U0001f1ea",
        "\U0001f4da Наташа! Твой ежедневный урок ждёт! /lesson",
        "\U0001f60a Привет, милая! Не забыла про твой немецкий? \U0001f916 Три слова в день = результат!",
    ],
    "dering": [
        "\U0001f4cb Наталья. Время учиться. /lesson",
        "\U0001f550 Ежедневное напоминание. /quiz",
        "\U0001f4d6 Урок ждёт. /lesson",
    ],
    "imperator": [
        "\U0001f525 Учись. /lesson",
        "\U0001f4ab Время пришло. /quiz",
        "\U0001f5e3 Немецкий ждёт. /lesson",
    ],
}


def _get_due_reminders(db_path: str, current_hhmm: str) -> list:
    """Alle aktiven Reminder die jetzt faellig sind (HH:MM)."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT r.telegram_id, r.user_id, u.teacher
            FROM reminders r
            JOIN users u ON r.user_id = u.id
            WHERE r.active = 1 AND r.remind_time = ?
            """,
            (current_hhmm,),
        ).fetchall()
        return [dict(r) for r in rows]


async def reminder_loop(bot, db_path: str) -> None:
    """Laeuft im Hintergrund, prueft jede Minute ob Erinnerungen faellig sind."""
    import random

    logger.info("Reminder loop started.")
    while True:
        try:
            now = datetime.now(tz=BERLIN)
            hhmm = now.strftime("%H:%M")
            due = _get_due_reminders(db_path, hhmm)

            for r in due:
                teacher = r.get("teacher", "vitali")
                msgs = TEACHER_REMIND_MSGS.get(teacher, TEACHER_REMIND_MSGS["vitali"])
                msg = random.choice(msgs)
                try:
                    await bot.send_message(chat_id=r["telegram_id"], text=msg)
                    logger.info("Reminder sent to telegram_id=%s", r["telegram_id"])
                except Exception as e:
                    logger.warning("Failed to send reminder to %s: %s", r["telegram_id"], e)

        except Exception as e:
            logger.error("Reminder loop error: %s", e, exc_info=True)

        # Naechste volle Minute abwarten
        now = datetime.now(tz=BERLIN)
        seconds_to_next = 60 - now.second
        await asyncio.sleep(seconds_to_next)
