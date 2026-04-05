"""Aussprache-Handler: Voice-Nachricht -> Transkription -> Bewertung vs. Zielwort."""
from __future__ import annotations

import logging
import sqlite3
import tempfile
from pathlib import Path
from difflib import SequenceMatcher

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

PRONUNCIATION_SESSION_KEY = "pronunciation_target"


def _similarity_score(a: str, b: str) -> int:
    """Einfacher Aehnlichkeitsscore 0-100 (case-insensitive)."""
    ratio = SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()
    return round(ratio * 100)


def _save_pronunciation_log(
    db_path: str, user_id: int, vocab_id: int | None, target: str, spoken: str, score: int
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO pronunciation_log (user_id, vocab_id, target_text, spoken_text, score) VALUES (?,?,?,?,?)",
            (user_id, vocab_id, target, spoken, score),
        )


FEEDBACK = {
    "vitali": {
        "excellent": "\U0001f3c6 Прекрасно! *{score}%* \u2014 отличное произношение!\n\U0001f1e9\U0001f1ea Цель: *{target}*\n\U0001f3a4 Ты сказала: _{spoken}_",
        "good": "\U0001f44d Хорошо! *{score}%* \u2014 почти правильно!\n\U0001f1e9\U0001f1ea Цель: *{target}*\n\U0001f3a4 Ты сказала: _{spoken}_\n\nпопробуй ещё раз!",
        "try_again": "\U0001f4aa Не сдавайся! *{score}%*\n\U0001f1e9\U0001f1ea Цель: *{target}*\n\U0001f3a4 Ты сказала: _{spoken}_\n\nПрочитай медленно и повтори!",
    },
    "dering": {
        "excellent": "\u2705 *{score}%* \u2014 верно. *{target}* / _{spoken}_",
        "good": "\U0001f4cb *{score}%*. *{target}* / _{spoken}_. Повтори.",
        "try_again": "\u274c *{score}%*. *{target}* / _{spoken}_. Снова.",
    },
    "imperator": {
        "excellent": "\U0001f525 *{score}%*. *{target}*. \u0425орошо.",
        "good": "*{score}%*. *{target}* / _{spoken}_.",
        "try_again": "\u274c *{score}%*. _{spoken}_ \u2260 *{target}*.",
    },
}


async def start_pronunciation(
    update: Update, context: ContextTypes.DEFAULT_TYPE, word_de: str, vocab_id: int | None = None
) -> None:
    """Setzt Zielwort und fordert Natasha auf zu sprechen."""
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)

    context.user_data[PRONUNCIATION_SESSION_KEY] = {"word": word_de, "vocab_id": vocab_id}

    prompts = {
        "vitali": f"\U0001f3a4 Теперь произнеси немецкое слово:\n\n*{word_de}*\n\nГовори чётко!",
        "dering": f"\U0001f3a4 Произнесите: *{word_de}*",
        "imperator": f"\U0001f3a4 *{word_de}*. Говори.",
    }
    prompt = prompts.get(teacher, prompts["vitali"])
    await update.message.reply_text(prompt, parse_mode="Markdown")


async def evaluate_pronunciation(
    update: Update, context: ContextTypes.DEFAULT_TYPE, transcribed_text: str
) -> None:
    """Vergleicht gesprochenen Text mit Zielwort."""
    session = context.user_data.get(PRONUNCIATION_SESSION_KEY)
    if not session:
        return  # Keine aktive Sitzung

    services = context.bot_data.get("services", {})
    settings = context.bot_data.get("settings")
    user_repo = services.get("user_repo")

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)

    target = session["word"]
    vocab_id = session.get("vocab_id")
    score = _similarity_score(target, transcribed_text)

    # In DB loggen
    if settings:
        try:
            _save_pronunciation_log(
                settings.database_path, user_id, vocab_id, target, transcribed_text, score
            )
        except Exception as e:
            logger.warning("Could not save pronunciation log: %s", e)

    # Feedback-Kategorie
    if score >= 85:
        category = "excellent"
    elif score >= 60:
        category = "good"
    else:
        category = "try_again"

    feedback_tpl = FEEDBACK.get(teacher, FEEDBACK["vitali"]).get(category, "")
    feedback = feedback_tpl.format(score=score, target=target, spoken=transcribed_text)

    await update.message.reply_text(feedback, parse_mode="Markdown")

    if category == "excellent":
        context.user_data.pop(PRONUNCIATION_SESSION_KEY, None)
    # Bei gut/schlecht: Session bleibt, damit Natasha nochmal versuchen kann
