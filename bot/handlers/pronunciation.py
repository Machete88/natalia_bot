"""Aussprache-Uebung: Nutzer spricht ein vorgegebenes deutsches Wort."""
from __future__ import annotations

import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from services.pronunciation import evaluate_pronunciation, format_feedback

logger = logging.getLogger(__name__)

PRONUNCIATION_SESSION_KEY = "pronunciation_target"

PROMPT_MSG = "\U0001f525 Говори: *{word}*"

NO_STT_MSG = (
    "\U0001f50a Для проверки произношения нужен локальный Whisper.\n"
    "Установи: `STT_PROVIDER=whisper_local` в .env"
)


async def handle_pronounce(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/pronounce [word] - Startet eine Aussprache-Uebung."""
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    tts = services.get("tts")
    voice_pipeline = services.get("voice_pipeline")
    settings = context.bot_data.get("settings")

    if not user_repo:
        await update.message.reply_text("Сервис недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    args = context.args
    if args:
        word = " ".join(args)
    else:
        import sqlite3, random
        if settings:
            with sqlite3.connect(settings.database_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT word_de FROM vocab_items ORDER BY RANDOM() LIMIT 1"
                ).fetchone()
                word = row["word_de"] if row else "Hallo"
        else:
            word = "Hallo"

    context.user_data[PRONUNCIATION_SESSION_KEY] = word

    prompt = PROMPT_MSG.format(word=word)
    await update.message.reply_text(prompt, parse_mode="Markdown")

    if tts and voice_pipeline:
        try:
            voice_id = voice_pipeline.voice_map.get("imperator", "imperator")
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(word, voice_id)
            with open(str(audio_file), "rb") as f:
                await update.message.reply_voice(voice=f, caption=f"\U0001f1e9\U0001f1ea {word}")
        except Exception as e:
            logger.warning("TTS for pronounce failed: %s", e)


async def handle_voice_pronunciation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Wird von voice-handler aufgerufen wenn pronunciation_target aktiv ist.
    Gibt True zurueck wenn verarbeitet, sonst False.
    """
    target_word = context.user_data.get(PRONUNCIATION_SESSION_KEY)
    if not target_word:
        return False

    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    settings = context.bot_data.get("settings")

    user = update.effective_user
    if not user_repo:
        return False

    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    stt = services.get("stt")
    from services.stt import MockSTTProvider
    if isinstance(stt, MockSTTProvider):
        await update.message.reply_text(NO_STT_MSG)
        context.user_data.pop(PRONUNCIATION_SESSION_KEY, None)
        return True

    try:
        tg_file = await context.bot.get_file(update.message.voice.file_id)
        audio_dir = Path("media/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)
        local_path = audio_dir / f"pronounce_{user.id}_{update.message.voice.file_unique_id}.ogg"
        await tg_file.download_to_drive(str(local_path))
    except Exception as e:
        logger.error("Pronunciation audio download failed: %s", e)
        await update.message.reply_text("Не удалось загрузить аудио.")
        return True

    try:
        recognised = await stt.transcribe(local_path)
    except Exception as e:
        logger.error("STT failed: %s", e)
        await update.message.reply_text("Не удалось распознать речь.")
        return True

    result = evaluate_pronunciation(target_word, recognised)
    feedback = format_feedback(result, "imperator")

    context.user_data.pop(PRONUNCIATION_SESSION_KEY, None)

    await update.message.reply_text(feedback, parse_mode="Markdown")

    if result["grade"] in ("perfect", "good"):
        await update.message.reply_text("\U0001f525 Дальше. /pronounce")

    return True
