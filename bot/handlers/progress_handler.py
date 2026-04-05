"""Erweiterter /progress Handler mit Streak-Kalender."""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.streak import get_streak, streak_emoji, streak_calendar

logger = logging.getLogger(__name__)


async def cmd_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services  = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    user      = update.effective_user

    teacher = "vitali"
    uid     = None
    if user_repo:
        uid     = user_repo.get_or_create_user(user.id, user.first_name or "")
        teacher = user_repo.get_teacher(uid)

    db = services.get("db")
    if not db or not uid:
        await update.message.reply_text("\u274c Keine Daten verfuegbar.")
        return

    # Vokabel-Stats
    total    = db.execute("SELECT COUNT(*) n FROM vocab_items").fetchone()[0]
    mastered = db.execute("SELECT COUNT(*) n FROM vocab_progress WHERE user_id=? AND status='mastered'", (uid,)).fetchone()[0]
    learning = db.execute("SELECT COUNT(*) n FROM vocab_progress WHERE user_id=? AND status='learning'",  (uid,)).fetchone()[0]
    new_     = max(0, total - mastered - learning)

    # Quiz-Stats
    quiz_total   = db.execute("SELECT COALESCE(SUM(correct_streak),0) FROM vocab_progress WHERE user_id=?", (uid,)).fetchone()[0]
    quiz_correct = quiz_total

    # Streak
    streak = get_streak(db, uid)
    count  = streak["count"]
    best   = streak["best"]
    emoji  = streak_emoji(count)

    # 7-Tage Kalender
    cal = streak_calendar(db, uid, days=7)

    level = user_repo.get_level(uid) if user_repo else "a1"

    teacher_headers = {
        "vitali":    f"\U0001f4ca *Dein Fortschritt, {user.first_name}!*",
        "dering":    f"\U0001f4ca *Fortschritt von {user.first_name}:*",
        "imperator": f"\U0001f525 *STATUS-REPORT: {user.first_name.upper()}*",
    }
    header = teacher_headers.get(teacher, teacher_headers["vitali"])

    text = (
        f"{header}\n\n"
        f"\U0001f4da *Vokabeln* (Level: {level.upper()})\n"
        f"  \U0001f7e9 Gemeistert: {mastered}\n"
        f"  \U0001f4d6 In Bearbeitung: {learning}\n"
        f"  \u2b1c Neu: {new_}\n"
        f"  Gesamt: {total}\n\n"
        f"{emoji} *Streak: {count} Tage* (Rekord: {best})\n"
        f"Letzte 7 Tage: {cal}\n\n"
        f"\U0001f3af *Quiz*: {quiz_correct} richtig von {quiz_total}\n\n"
    )

    if count >= 7:
        motivations = {
            "vitali":    "\U0001f3c6 Eine ganze Woche! Du bist unglaublich!",
            "dering":    "\U0001f3c6 7+ Tage. Sehr konsequent.",
            "imperator": "\U0001f3c6 7 Tage. Das ist der Mindeststandard.",
        }
        text += motivations.get(teacher, motivations["vitali"])
    elif count >= 3:
        motivations = {
            "vitali":    "\U0001f4aa Sehr gut! Halte den Schwung!",
            "dering":    "\U0001f4aa Guter Start!",
            "imperator": "\U0001f525 Weiter so.",
        }
        text += motivations.get(teacher, motivations["vitali"])
    else:
        motivations = {
            "vitali":    "\U0001f31f Fang heute an und bau deinen Streak auf!",
            "dering":    "\u2728 Jeden Tag lernen!",
            "imperator": "\U0001f525 Taeglich. Kein Tag aussetzen.",
        }
        text += motivations.get(teacher, motivations["vitali"])

    await update.message.reply_text(text, parse_mode="Markdown")
