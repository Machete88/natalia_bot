from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    dialogue_router = services.get("dialogue_router")
    voice_pipeline = services.get("voice_pipeline")  # nutzen wir für TTS
    tts = services.get("tts")

    if not dialogue_router or not user_repo or not tts:
        await update.message.reply_text("Сервис временно недоступен. Попробуй позже.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")

    try:
        # Text -> LLM
        result = await dialogue_router.generate_reply(user_id, update.message.text or "")
        reply_text = result["text"]
        teacher = result.get("teacher", "vitali")

        # Lehrername -> Voice-ID macht schon VoicePipeline / runtime_init
        voice_map = services.get("voice_pipeline").voice_map if voice_pipeline else {}
        voice_id = voice_map.get(teacher.lower(), teacher)

        # Text -> TTS
        audio_file = await tts.synthesize(reply_text, voice_id)

        # Nur Voice schicken
        with open(str(audio_file), "rb") as f:
            await update.message.reply_voice(voice=f)

    except Exception as e:
        logger.error("Text handler error: %s", e, exc_info=True)
        await update.message.reply_text("Извини, произошла ошибка. Попробуй ещё раз!")