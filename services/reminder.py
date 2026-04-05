"""Taegliche Lern-Erinnerung per Telegram.

Konfiguration in .env:
  DAILY_REMINDER_TIME=09:00
  TIMEZONE=Europe/Berlin

Natalia kann ihren eigenen Zeitplan setzen:
  /remind 08:30  -> Erinnerung um 08:30
  /remind off    -> Erinnerung deaktivieren
"""
from __future__ import annotations
import logging
import os
import random
from datetime import time
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes, Application

logger = logging.getLogger(__name__)

REMINDER_MESSAGES = {
    "vitali": [
        "\U0001f31e Guten Morgen, Natalia! Zeit fuer deine taegliche Deutsch-Lektion. /lesson",
        "\U0001f4da Heute wieder ein bisschen Deutsch? /lesson oder /quiz",
        "\U0001f1e9\U0001f1ea Dein Deutsch wartet auf dich! Nur 5 Minuten. /lesson",
        "\U0001f525 Streak halten! Lern heute deine Vokabeln. /quiz",
    ],
    "dering": [
        "\U0001f1e9\U0001f1ea Guten Morgen! Deine Lektion wartet. /lesson",
        "\U0001f4d6 Heute wieder Deutsch? Los geht's! /quiz",
        "\U0001f525 Keine Pause! Lern weiter. /lesson",
        "\U0001f4aa Ein kurzes Quiz? /quiz",
    ],
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


async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job-Funktion: sendet Erinnerung an Natalia."""
    job = context.job
    chat_id = job.data["chat_id"]
    teacher = job.data.get("teacher", "vitali")
    msgs = REMINDER_MESSAGES.get(teacher, REMINDER_MESSAGES["vitali"])
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
    teacher: str = "vitali",
) -> None:
    """Sendet Erinnerung direkt (ohne Job-Queue)."""
    msgs = REMINDER_MESSAGES.get(teacher, REMINDER_MESSAGES["vitali"])
    msg = random.choice(msgs)
    try:
        await bot.send_message(chat_id=telegram_id, text=msg)
        logger.info("Daily reminder sent to %s", telegram_id)
    except Exception as e:
        logger.warning("Reminder send failed: %s", e)


def schedule_reminder(app: Application, chat_id: int, reminder_time: time, teacher: str = "vitali") -> None:
    """Registriert den taegl. Reminder-Job."""
    tz = _get_tz()
    job_name = f"reminder_{chat_id}"
    current = app.job_queue.get_jobs_by_name(job_name)
    for job in current:
        job.schedule_removal()
    app.job_queue.run_daily(
        send_reminder,
        time=reminder_time.replace(tzinfo=tz),
        name=job_name,
        data={"chat_id": chat_id, "teacher": teacher},
    )
    logger.info("Reminder scheduled for %s at %s (%s)", chat_id, reminder_time, teacher)


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
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    user = update.effective_user

    teacher = "vitali"
    if user_repo:
        uid = user_repo.get_or_create_user(user.id, user.first_name or "")
        teacher = user_repo.get_teacher(uid)

        def _save(t_str):
            try:
                user_repo._db.execute(
                    "INSERT OR REPLACE INTO user_preferences (user_id, key, value) VALUES (?,?,?)",
                    (uid, "reminder_time", t_str)
                )
                user_repo._db.commit()
            except Exception:
                pass
    else:
        def _save(t_str):
            pass

    teacher_labels = {"vitali": "Vitali", "dering": "Dering", "imperator": "der Imperator"}
    label = teacher_labels.get(teacher, "ich")

    if not args:
        await update.message.reply_text(
            "\U0001f4ac Nutzung:\n"
            "/remind 09:00 — Erinnerung um 09:00 Uhr\n"
            "/remind off — Erinnerung deaktivieren"
        )
        return

    arg = args[0].lower()

    if arg == "off":
        removed = remove_reminder(context.application, chat_id)
        _save("off")
        if removed:
            replies = {
                "vitali":    "\U0001f44c OK, ich erinnere dich nicht mehr. Du kannst jederzeit /remind 09:00 setzen.",
                "dering":    "\U0001f44c Erinnerung deaktiviert.",
                "imperator": "\U0001f525 Deaktiviert. Aber vergiss nicht selbst zu lernen!",
            }
        else:
            replies = {
                "vitali":    "Es gab keine aktive Erinnerung.",
                "dering":    "Keine Erinnerung aktiv.",
                "imperator": "Keine aktive Erinnerung gefunden.",
            }
        await update.message.reply_text(replies.get(teacher, replies["vitali"]))
        return

    t = parse_time(arg)
    if not t:
        await update.message.reply_text("\u274c Format: /remind 09:30 (HH:MM)")
        return

    schedule_reminder(context.application, chat_id, t, teacher)
    _save(arg)

    replies = {
        "vitali":    f"\u23f0 Erledigt! {label} erinnert dich taeglich um {arg} Uhr. /remind off zum Deaktivieren.",
        "dering":    f"\u23f0 Erinnerung gesetzt: {arg} Uhr.",
        "imperator": f"\U0001f525 {arg} Uhr. Ich erwarte dich. Sei bereit.",
    }
    await update.message.reply_text(replies.get(teacher, replies["vitali"]))
