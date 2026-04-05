"""Voice message handler mit Aussprache-Check-Integration."""
from __future__ import annotations

import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verarbeitet Sprachnachrichten.
    - Wenn pronunciation_session aktiv: Aussprache-Bewertung
    - Sonst: STT -> DialogueRouter -> TTS-Antwort
    """
    # Pronunciation-Check zuerst pruefen
    from bot.handlers.pronunciation import handle_voice_pronunciation
    handled = await handle_voice_pronunciation(update, context)
    if handled:
        return

    # Normaler Voice-Flow
    services = context.bot_data.get("services", {})
    settings = context.bot_data.get("settings")
    user_repo = services.get("user_repo")
    voice_pipeline = services.get("voice_pipeline")
    dialogue_router = services.get("dialogue_router")
    tts = services.get("tts")

    if not user_repo or not voice_pipeline:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)

    await context.bot.send_chat_action(update.effective_chat.id, action="typing")

    try:
        tg_file = await context.bot.get_file(update.message.voice.file_id)
        audio_dir = Path("media/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)
        local_path = audio_dir / f"voice_{user.id}_{update.message.voice.file_unique_id}.ogg"
        await tg_file.download_to_drive(str(local_path))
    except Exception as e:
        logger.error("Voice download failed: %s", e)
        await update.message.reply_text("Не удалось загрузить аудио.")
        return

    stt = services.get("stt")
    try:
        text = await stt.transcribe(local_path)
    except Exception as e:
        logger.warning("STT failed, using placeholder: %s", e)
        text = "[voice message]"

    if not text or text.strip() == "[voice message]":
        await update.message.reply_text("Не удалось распознать речь. Попробуй ещё раз.")
        return

    # STT-Transkript zeigen
    await update.message.reply_text(f"\U0001f4dd Распознано: _{text}_", parse_mode="Markdown")

    if not dialogue_router:
        return

    await context.bot.send_chat_action(update.effective_chat.id, action="typing")
    try:
        response_text = await dialogue_router.route(user_id=user_id, text=text)
    except Exception as e:
        logger.error("DialogueRouter error: %s", e)
        response_text = "Извини, произошла ошибка."

    await update.message.reply_text(response_text)

    if tts and voice_pipeline:
        try:
            voice_map = voice_pipeline.voice_map
            voice_id = voice_map.get(teacher.lower(), teacher)
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(response_text, voice_id)
            with open(str(audio_file), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS failed: %s", e)
