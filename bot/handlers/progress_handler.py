"""Erweiterter /progress Handler — Herr Imperator Stil."""
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

    uid = None
    if user_repo:
        uid = user_repo.get_or_create_user(user.id, user.first_name or "")

    db = services.get("db")
    if not db or not uid:
        await update.message.reply_text("\u274c Данные недоступны.")
        return

    total    = db.execute("SELECT COUNT(*) n FROM vocab_items").fetchone()[0]
    mastered = db.execute("SELECT COUNT(*) n FROM vocab_progress WHERE user_id=? AND status='mastered'", (uid,)).fetchone()[0]
    learning = db.execute("SELECT COUNT(*) n FROM vocab_progress WHERE user_id=? AND status='learning'",  (uid,)).fetchone()[0]
    new_     = max(0, total - mastered - learning)

    quiz_total = db.execute("SELECT COALESCE(SUM(correct_streak),0) FROM vocab_progress WHERE user_id=?", (uid,)).fetchone()[0]

    streak = get_streak(db, uid)
    count  = streak["count"]
    best   = streak["best"]
    emoji  = streak_emoji(count)

    cal   = streak_calendar(db, uid, days=7)
    level = user_repo.get_level(uid) if user_repo else "a1"

    text = (
        f"\U0001f525 *РАПОРТ РЕКРУТА: {user.first_name.upper()}*\n\n"
        f"\U0001f4da *Словарный запас* (Уровень: {level.upper()})\n"
        f"  \U0001f7e9 Покорено: {mastered}\n"
        f"  \U0001f4d6 В процессе: {learning}\n"
        f"  \u2b1c Не изучено: {new_}\n"
        f"  Всего: {total}\n\n"
        f"{emoji} *Серия: {count} дней* (Рекорд: {best})\n"
        f"Последние 7 дней: {cal}\n\n"
        f"\U0001f3af *Квиз*: {quiz_total} правильных\n\n"
    )

    if count >= 7:
        text += "\U0001f525 7 дней подряд. Господин Император\u2026 впечатлён. _Почти._"
    elif count >= 3:
        text += "\U0001f4aa 3 дня. Хорошее начало. Не останавливайся, Рекрут."
    else:
        text += "\U0001f525 Ежедневно. Ни одного пропуска. Это приказ Господина Императора."

    await update.message.reply_text(text, parse_mode="Markdown")
