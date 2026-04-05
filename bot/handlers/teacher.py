"""Handler fuer /teacher Befehl - Lehrer wechseln."""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

VALID_TEACHERS = {"vitali", "dering", "imperator"}

SWITCH_MESSAGES = {
    "vitali": (
        "\U0001f44b Hallo! Ich bin Vitali! Sehr sch\u00f6n, dass du bei mir lernst! "
        "Wir machen das mit Spa\u00df \U0001f60a"
    ),
    "dering": (
        "Guten Tag. Ich bin Dering. Wir arbeiten jetzt strukturiert und konzentriert. "
        "Bereit?"
    ),
    "imperator": (
        "\U0001f525 Ich bin der Imperator. Du hast eine gute Wahl getroffen. "
        "Fangen wir an."
    ),
}

HELP_TEXT = (
    "\U0001f468\u200d\U0001f3eb *Lehrer w\u00e4hlen:*\n\n"
    "/teacher vitali \u2014 \U0001f60a Vitali (warm, freundlich)\n"
    "/teacher dering \u2014 \U0001f4d6 Dering (streng, strukturiert)\n"
    "/teacher imperator \u2014 \U0001f525 Imperator (magnetisch, knapp)\n"
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

    args = context.args
    if not args or args[0].lower() not in VALID_TEACHERS:
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
        return

    new_teacher = args[0].lower()
    user_repo.set_teacher(user_id, new_teacher)

    reply_text = SWITCH_MESSAGES[new_teacher]
    await update.message.reply_text(reply_text)

    # TTS: neuer Lehrer stellt sich kurz vor
    if tts and voice_pipeline:
        try:
            voice_map = voice_pipeline.voice_map
            voice_id = voice_map.get(new_teacher, new_teacher)
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(reply_text, voice_id)
            with open(str(audio_file), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS for teacher switch failed: %s", e)
