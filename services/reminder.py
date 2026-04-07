"""Taegliche Lern-Erinnerung per Telegram."""
from __future__ import annotations
import logging
import os
import random
import sqlite3
from datetime import date, datetime, timedelta
from datetime import time
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes, Application

logger = logging.getLogger(__name__)

REMINDER_MESSAGES = {
    "imperator": [
        "\U0001f525 STEH AUF. LERN. JETZT. /lesson",
        "\U0001f4aa Kein Ausrede. Deutsch. Jetzt. /quiz",
        "\U0001f1e9\U0001f1ea Der Imperator erwartet Fortschritt. /lesson",
        "\U0001f525 Taegliches Training. Keine Ausnahmen. /quiz",
    ],
}


def _get_tz() -> ZoneInfo:
    tz_name = os.getenv("TIMEZONE", "Europe/Berlin")
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("Europe/Berlin")


def parse_time(time_str: str) -> time | None:
    """Parst '09:30' -> time(9, 30). Gibt None zurueck bei Fehler."""
    try:
        h, m = time_str.strip().split(":")
        return time(int(h), int(m))
    except Exception:
        return None


def update_streak(db_path: str, user_id: int, today: str | None = None) -> int:
    """Aktualisiert den Lern-Streak fuer user_id in user_preferences.

    Regeln:
      - Selber Tag wie last_learned -> kein Doppelzaehlen
      - Gestern als last_learned    -> Streak + 1
      - Alles andere                -> Streak = 1 (Reset)
    Gibt den aktuellen Streak-Wert zurueck.
    """
    today_str = today or date.today().strftime("%Y-%m-%d")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        def _get(key: str) -> str | None:
            row = conn.execute(
                "SELECT value FROM user_preferences WHERE user_id=? AND key=?",
                (user_id, key),
            ).fetchone()
            return row["value"] if row else None

        def _set(key: str, value: str) -> None:
            conn.execute(
                "INSERT OR REPLACE INTO user_preferences (user_id, key, value) VALUES (?,?,?)",
                (user_id, key, value),
            )

        last_learned = _get("last_learned")
        streak_val = int(_get("streak") or "0")

        if last_learned == today_str:
            return streak_val

        yesterday = (datetime.strptime(today_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        if last_learned == yesterday:
            streak_val += 1
        else:
            streak_val = 1

        _set("last_learned", today_str)
        _set("streak", str(streak_val))
        conn.commit()

    return streak_val


async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job-Funktion: sendet Erinnerung."""
    job = context.job
    chat_id = job.data["chat_id"]
    msgs = REMINDER_MESSAGES["imperator"]
    msg = random.choice(msgs)
    try:
        await context.bot.send_message(chat_id=chat_id, text=msg)
        logger.info("Daily reminder sent to %s", chat_id)
    except Exception as e:
        logger.warning("Reminder send failed: %s", e)


async def send_daily_reminder(
    bot,
    db_path: str,
    telegram_id: int,
    user_id: int,
    teacher: str = "imperator",
) -> None:
    """Sendet Erinnerung direkt (ohne Job-Queue)."""
    msgs = REMINDER_MESSAGES["imperator"]
    msg = random.choice(msgs)
    try:
        await bot.send_message(chat_id=telegram_id, text=msg)
        logger.info("Daily reminder sent to %s", telegram_id)
    except Exception as e:
        logger.warning("Reminder send failed: %s", e)


def schedule_reminder(app: Application, chat_id: int, reminder_time: time, teacher: str = "imperator") -> None:
    tz = _get_tz()
    job_name = f"reminder_{chat_id}"
    current = app.job_queue.get_jobs_by_name(job_name)
    for job in current:
        job.schedule_removal()
    app.job_queue.run_daily(
        send_reminder,
        time=reminder_time.replace(tzinfo=tz),
        name=job_name,
        data={"chat_id": chat_id},
    )
    logger.info("Reminder scheduled for %s at %s", chat_id, reminder_time)


def remove_reminder(app: Application, chat_id: int) -> bool:
    job_name = f"reminder_{chat_id}"
    jobs = app.job_queue.get_jobs_by_name(job_name)
    for job in jobs:
        job.schedule_removal()
    return len(jobs) > 0


async def cmd_remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler fuer /remind HH:MM oder /remind off."""
    args = context.args
    chat_id = update.effective_chat.id

    if not args:
        await update.message.reply_text(
            "\U0001f4ac Nutzung:\n"
            "/remind 09:00 \u2014 Erinnerung um 09:00 Uhr\n"
            "/remind off \u2014 Erinnerung deaktivieren"
        )
        return

    arg = args[0].lower()

    if arg == "off":
        removed = remove_reminder(context.application, chat_id)
        if removed:
            await update.message.reply_text("\U0001f525 Deaktiviert. Aber vergiss nicht selbst zu lernen!")
        else:
            await update.message.reply_text("Keine aktive Erinnerung gefunden.")
        return

    t = parse_time(arg)
    if not t:
        await update.message.reply_text("\u274c Format: /remind 09:30 (HH:MM)")
        return

    schedule_reminder(context.application, chat_id, t)
    await update.message.reply_text(f"\U0001f525 {arg} Uhr. Ich erwarte dich. Sei bereit.")
