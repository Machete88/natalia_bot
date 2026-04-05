"""Telegram-Handler fuer /pronounce Befehl und Voice-Aussprache-Training.

Kommt nach /lesson automatisch optional:
  'Moechtest du das Wort aussprechen? /pronounce'

Oder direkt: /pronounce Wort
"""
from __future__ import annotations
import logging
import os
import tempfile
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from services.pronunciation import (
    score_pronunciation, build_pronounce_prompt, build_result_message, PRONOUNCE_KEY
)

logger = logging.getLogger(__name__)


async def cmd_pronounce(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler fuer /pronounce [wort]."""
    services  = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    user      = update.effective_user

    teacher = "vitali"
    if user_repo:
        uid = user_repo.get_or_create_user(user.id, user.first_name or "")
        teacher = user_repo.get_teacher(uid)

    # Wort aus Argument oder letzter Lektion
    word = " ".join(context.args) if context.args else context.user_data.get("last_lesson_word", "")

    if not word:
        # Zufaelliges Wort aus DB
        db = services.get("db")
        if db:
            row = db.execute("SELECT word_de FROM vocab_items ORDER BY RANDOM() LIMIT 1").fetchone()
            word = row[0] if row else "Guten Morgen"
        else:
            word = "Guten Morgen"

    context.user_data[PRONOUNCE_KEY] = word
    prompt = build_pronounce_prompt(word, teacher)
    await update.message.reply_text(prompt, parse_mode="Markdown")


async def handle_voice_pronounce(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Verarbeitet Sprachnachricht wenn Aussprache-Modus aktiv.
    Gibt True zurueck wenn verarbeitet, False wenn weitergeleitet werden soll.
    """
    target_word = context.user_data.get(PRONOUNCE_KEY)
    if not target_word:
        return False

    services  = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    stt       = services.get("stt")
    user      = update.effective_user

    teacher = "vitali"
    if user_repo:
        uid = user_repo.get_or_create_user(user.id, user.first_name or "")
        teacher = user_repo.get_teacher(uid)

    await update.message.reply_text("\U0001f50a Ich hoere zu...")

    # Sprachnachricht herunterladen und transkribieren
    voice_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await voice_file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    spoken_text = ""
    if stt:
        try:
            spoken_text = await stt.transcribe(tmp_path)
        except Exception as e:
            logger.warning("STT error in pronounce: %s", e)
    else:
        # Mock-Modus: nimm Zielwort als korrekte Aussprache
        spoken_text = target_word

    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    result  = score_pronunciation(target_word, spoken_text or "")
    msg     = build_result_message(target_word, result, teacher)

    await update.message.reply_text(msg, parse_mode="Markdown")

    # Aussprache-Modus beenden nach Bewertung
    context.user_data.pop(PRONOUNCE_KEY, None)
    return True


pronounce_handler = CommandHandler("pronounce", cmd_pronounce)
