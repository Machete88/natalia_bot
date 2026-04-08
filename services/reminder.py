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
    """Aktualisiert den Lern-Streak fuer user_id in user_preferences."""
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
    logger.info("Reminder scheduled for chat_id=%s at %s", chat_id, reminder_time)


async def cmd_remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler fuer /remind [HH:MM | off]."""
    settings = context.bot_data.get("settings")
    app = context.application
    chat_id = update.effective_chat.id

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "\u23f0 *Erinnerung einrichten:*\n"
            "/remind 09:00 \u2014 taeglich um 09:00 Uhr\n"
            "/remind off \u2014 deaktivieren",
            parse_mode="Markdown",
        )
        return

    arg = args[0].lower()

    if arg == "off":
        job_name = f"reminder_{chat_id}"
        jobs = app.job_queue.get_jobs_by_name(job_name)
        for job in jobs:
            job.schedule_removal()
        # DB aktualisieren
        if settings:
            try:
                import sqlite3 as _sq
                with _sq.connect(settings.database_path) as conn:
                    conn.execute(
                        "UPDATE reminders SET active=0 WHERE telegram_id=?",
                        (chat_id,),
                    )
                    conn.commit()
            except Exception as e:
                logger.warning("Reminder DB update failed: %s", e)
        await update.message.reply_text("\u2705 Erinnerung deaktiviert.")
        return

    t = parse_time(arg)
    if not t:
        await update.message.reply_text(
            "\u274c Ungueltige Zeit. Beispiel: /remind 09:00"
        )
        return

    schedule_reminder(app, chat_id, t)

    # In DB speichern
    if settings:
        try:
            import sqlite3 as _sq
            with _sq.connect(settings.database_path) as conn:
                conn.execute(
                    """
                    INSERT INTO reminders (telegram_id, remind_time, active)
                    VALUES (?, ?, 1)
                    ON CONFLICT(telegram_id) DO UPDATE SET remind_time=excluded.remind_time, active=1
                    """,
                    (chat_id, arg),
                )
                conn.commit()
        except Exception as e:
            logger.warning("Reminder DB save failed: %s", e)

    await update.message.reply_text(
        f"\u23f0 Erinnerung gesetzt fuer *{arg}* Uhr.\n"
        "/remind off zum Deaktivieren.",
        parse_mode="Markdown",
    )
