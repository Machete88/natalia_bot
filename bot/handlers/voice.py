"""Voice-Handler: STT -> Pronunciation-Check ODER normaler Dialogue."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.pronunciation import PRONUNCIATION_SESSION_KEY, evaluate_pronunciation

logger = logging.getLogger(__name__)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    voice_pipeline = services.get("voice_pipeline")
    dialogue_router = services.get("dialogue_router")
    tts = services.get("tts")
    user_repo = services.get("user_repo")

    if not voice_pipeline or not user_repo:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)

    await context.bot.send_chat_action(update.effective_chat.id, action="typing")

    # Voice-Datei herunterladen
    try:
        tg_file = await context.bot.get_file(update.message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        await tg_file.download_to_drive(str(tmp_path))
    except Exception as e:
        logger.error("Voice download failed: %s", e, exc_info=True)
        await update.message.reply_text("Не удалось загрузить голосовое сообщение.")
        return

    # STT
    try:
        transcribed = await voice_pipeline.transcribe(tmp_path)
    except Exception as e:
        logger.error("STT failed: %s", e, exc_info=True)
        transcribed = ""
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    if not transcribed:
        await update.message.reply_text("Не удалось распознать речь.")
        return

    # Wenn Aussprache-Session aktiv: Bewertung
    if context.user_data.get(PRONUNCIATION_SESSION_KEY):
        await evaluate_pronunciation(update, context, transcribed)
        return

    # Normaler Dialogue
    await context.bot.send_chat_action(update.effective_chat.id, action="typing")
    try:
        response_text = await dialogue_router.route(user_id=user_id, text=transcribed)
    except Exception as e:
        logger.error("DialogueRouter error: %s", e, exc_info=True)
        response_text = "Произошла ошибка. Попробуй ещё раз."

    # Zeige Transkription + Antwort
    await update.message.reply_text(f"\U0001f5e3 _{transcribed}_\n\n{response_text}", parse_mode="Markdown")

    if tts:
        try:
            voice_map = voice_pipeline.voice_map
            voice_id = voice_map.get(teacher.lower(), teacher)
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(response_text, voice_id)
            with open(str(audio_file), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS failed: %s", e)
