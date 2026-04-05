"""Text-Nachrichten Handler: leitet an DialogueRouter ODER Quiz-Auswertung ODER Support weiter."""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.quiz import QUIZ_SESSION_KEY, handle_quiz

logger = logging.getLogger(__name__)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    settings = context.bot_data.get("settings")
    user = update.effective_user

    # --- Support-Codewort pruefen ---
    if settings and hasattr(settings, "support_codeword") and settings.support_codeword:
        if text.lower() == settings.support_codeword.lower():
            from bot.handlers.support import activate_support
            await activate_support(update, context)
            return

    # --- /endsupport von Natalia ---
    if text.strip().lower() == "/endsupport":
        from bot.handlers.support import is_support_active, deactivate_support
        if is_support_active(context):
            await deactivate_support(update, context)
        return

    # --- Support-Modus aktiv: Nachrichten weiterleiten statt AI ---
    from bot.handlers.support import is_support_active, forward_to_admin
    if is_support_active(context) and settings and user.id == settings.authorized_user_id:
        await forward_to_admin(update, context)
        return

    # --- Admin schreibt: Antwort an Natalia weiterleiten ---
    if settings and user.id == settings.admin_user_id and user.id != settings.authorized_user_id:
        from bot.handlers.support import handle_admin_reply
        await handle_admin_reply(update, context)
        return

    # --- Quiz-Antwort 1-4 ---
    if context.user_data.get(QUIZ_SESSION_KEY) and text in {"1", "2", "3", "4"}:
        await handle_quiz(update, context)
        return

    # --- Normaler Dialogue-Router ---
    services = context.bot_data.get("services", {})
    dialogue_router = services.get("dialogue_router")
    tts = services.get("tts")
    voice_pipeline = services.get("voice_pipeline")
    user_repo = services.get("user_repo")

    if not dialogue_router or not user_repo:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)

    await context.bot.send_chat_action(update.effective_chat.id, action="typing")

    try:
        result = await dialogue_router.generate_reply(user_id=user_id, user_text=text)
        response_text = result["text"] if isinstance(result, dict) else str(result)
    except Exception as e:
        logger.error("DialogueRouter error: %s", e, exc_info=True)
        response_text = "Произошла ошибка. Попробуй ещё раз."

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
