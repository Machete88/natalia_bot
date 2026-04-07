"""Text-Nachrichten Handler — Natasha schreibt, Imperator antwortet."""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.quiz import QUIZ_SESSION_KEY, handle_quiz
from services.session_manager import get_session, LearningPhase

logger = logging.getLogger(__name__)

PRACTICE_CORRECT = [
    "\u2705 *{word_de}*.",
    "\u2705 Ричтиг. *{word_de}*.",
]

PRACTICE_WRONG = [
    "\u274c *{word_de}*. _{example}_",
    "\u274c Фальшо. *{word_de}*.",
]

PRACTICE_NEXT = "\u2757 *{word_ru}*:"
PRACTICE_DONE = "\U0001f525 Упражнение завершено. /quiz \u2014 если готова."


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    settings = context.bot_data.get("settings")
    user = update.effective_user

    # --- Support-Modus ---
    from bot.handlers.support import is_support_active, SUPPORT_MODE_KEY

    # 1. Codewort-Check (nur für Natasha)
    if settings and getattr(settings, "support_codeword", None):
        if (
            user.id == settings.authorized_user_id
            and text.lower() == settings.support_codeword.lower()
        ):
            from bot.handlers.support import activate_support
            await activate_support(update, context)
            return

    # 2. /endsupport als Text (Fallback)
    if text.strip().lower() == "/endsupport":
        if is_support_active(context):
            from bot.handlers.support import deactivate_support
            await deactivate_support(update, context)
        return

    # 3. Wenn Support aktiv: Natasha's Nachrichten an Admin weiterleiten
    if (
        is_support_active(context)
        and settings
        and user.id == settings.authorized_user_id
    ):
        from bot.handlers.support import forward_to_admin
        await forward_to_admin(update, context)
        return

    # 4. Admin antwortet — nur wenn er NICHT auch authorized_user ist
    if (
        settings
        and user.id == settings.admin_user_id
        and user.id != settings.authorized_user_id
        and is_support_active(context)
    ):
        from bot.handlers.support import handle_admin_reply
        await handle_admin_reply(update, context)
        return

    # --- /skip ---
    if text.lower() in ("/skip", "skip"):
        await _handle_skip(update, context)
        return

    # --- Practice-Phase ---
    session = get_session(context.user_data)
    if session.phase == LearningPhase.PRACTICE:
        await _handle_practice_answer(update, context, text, session)
        return

    # --- Quiz ---
    if context.user_data.get(QUIZ_SESSION_KEY) and text in {"1", "2", "3", "4"}:
        await handle_quiz(update, context)
        return

    # --- Normaler Chat mit Imperator ---
    services = context.bot_data.get("services", {})
    dialogue_router = services.get("dialogue_router")
    tts = services.get("tts")
    voice_pipeline = services.get("voice_pipeline")
    user_repo = services.get("user_repo")

    if not dialogue_router or not user_repo:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    await context.bot.send_chat_action(update.effective_chat.id, action="typing")

    try:
        result = await dialogue_router.generate_reply(user_id=user_id, user_text=text)
        response_text = result["text"] if isinstance(result, dict) else str(result)
    except Exception as e:
        logger.error("DialogueRouter error: %s", e, exc_info=True)
        response_text = "Произошла ошибка. Попробуй ещё раз."

    await update.message.reply_text(response_text)

    # TTS
    if tts and voice_pipeline and voice_pipeline.voice_id:
        try:
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(response_text, voice_pipeline.voice_id)
            with open(str(audio_file), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS failed: %s", e)


async def _handle_practice_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, session
) -> None:
    import random
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    lesson_planner = services.get("lesson_planner")
    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    word = session.current_practice_word()
    if not word:
        session.finish()
        return

    answer_clean = text.strip().lower().replace("der ", "").replace("die ", "").replace("das ", "")
    correct_clean = word["word_de"].lower().replace("der ", "").replace("die ", "").replace("das ", "")
    correct = answer_clean == correct_clean

    pool = PRACTICE_CORRECT if correct else PRACTICE_WRONG
    feedback = random.choice(pool).format(
        word_de=word["word_de"],
        example=word.get("example_de", ""),
    )
    await update.message.reply_text(feedback, parse_mode="Markdown")

    done = session.advance_practice(correct)

    if done:
        if lesson_planner and session.practice_results:
            lesson_planner.update_progress(user_id, session.practice_results)
        await update.message.reply_text(PRACTICE_DONE, parse_mode="Markdown")
        session.finish()
    else:
        next_word = session.current_practice_word()
        if next_word:
            msg = PRACTICE_NEXT.format(word_ru=next_word["word_ru"])
            await update.message.reply_text(
                msg + "\n\n_(/skip чтобы пропустить)_",
                parse_mode="Markdown",
            )


async def _handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    session = get_session(context.user_data)
    if session.phase != LearningPhase.PRACTICE:
        await update.message.reply_text("Сейчас нет активной упражнения.")
        return

    done = session.advance_practice(False)
    if done:
        session.finish()
        await update.message.reply_text(PRACTICE_DONE, parse_mode="Markdown")
    else:
        next_word = session.current_practice_word()
        if next_word:
            msg = PRACTICE_NEXT.format(word_ru=next_word["word_ru"])
            await update.message.reply_text(
                msg + "\n\n_(/skip чтобы пропустить)_",
                parse_mode="Markdown",
            )
