"""Voice message handler."""
from __future__ import annotations
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    voice_pipeline = services.get("voice_pipeline")
    dialogue_router = services.get("dialogue_router")

    if not voice_pipeline or not user_repo or not dialogue_router:
        # Falls irgendwas kaputt ist: kurze Textmeldung
        await update.message.reply_text("Голос сейчас недоступен, попробуй позже.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    # Zeige, dass der Bot gleich eine Sprachnachricht aufnimmt/sendet
    await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")

    try:
        voice = update.message.voice
        local_path = Path("media/audio") / f"voice_{voice.file_unique_id}.ogg"
        local_path.parent.mkdir(parents=True, exist_ok=True)

        tg_file = await context.bot.get_file(voice.file_id)
        await tg_file.download_to_drive(str(local_path))

        # Voice → Whisper → LLM → TTS
        reply_text, audio_file, teacher = await voice_pipeline.process(
            user_id, local_path, dialogue_router
        )

        # Nur Audio zurückschicken, keinen Text
        try:
            suffix = audio_file.suffix.lower()  # z.B. ".mp3" oder ".wav"
            if suffix not in {".mp3", ".wav", ".ogg", ".m4a"}:
                suffix = ".mp3"

            filename = f"reply{suffix}"

            with open(str(audio_file), "rb") as f:
                # WICHTIG: filename mit richtiger Endung hilft Telegram,
                # das Format zu erkennen und die Dauer korrekt anzuzeigen.
                await update.message.reply_audio(audio=f, filename=filename)
        except Exception as e:
            logger.warning("Audio reply failed, sending text only: %s", e)
            await update.message.reply_text(reply_text)

        # Eingangsdatei aufräumen
        try:
            local_path.unlink(missing_ok=True)
        except Exception:
            pass

    except Exception as e:
        logger.error("Voice handler error: %s", e, exc_info=True)
        await update.message.reply_text(
            "Прости, не смогла распознать голосовое. Давай позже ещё раз."
        )