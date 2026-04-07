"""Handler fuer /teacher — nur Imperator verfuegbar."""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

IMPERATOR_GREETING = (
    "\U0001f525 Ich bin der Imperator. Du hast eine gute Wahl getroffen. "
    "Fangen wir an."
)

HELP_TEXT = (
    "\U0001f468\u200d\U0001f3eb *Dein Lehrer:*\n\n"
    "Nur ein Lehrer ist verfügbar:\n"
    "/teacher imperator — \U0001f525 Imperator\n"
)


async def handle_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    tts = services.get("tts")
    voice_pipeline = services.get("voice_pipeline")

    if not user_repo:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    user_repo.set_teacher(user_id, "imperator")

    args = context.args
    # Show help if no valid arg given
    if not args or args[0].lower() != "imperator":
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
        return

    await update.message.reply_text(IMPERATOR_GREETING)

    if tts and voice_pipeline and voice_pipeline.voice_id:
        try:
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(IMPERATOR_GREETING, voice_pipeline.voice_id)
            with open(str(audio_file), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS for teacher switch failed: %s", e)
