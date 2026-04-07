"""Text-Nachrichten Handler mit vollständigem Session-Management."""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.quiz import QUIZ_SESSION_KEY, handle_quiz
from services.session_manager import get_session, LearningPhase, clear_session

logger = logging.getLogger(__name__)

PRACTICE_CORRECT = {
    "vitali": ["✅ *Отлично!* {word_de} \u2014 правильно! 🎉", "✅ Да! *{word_de}* \u2014 молодец! 👏"],
    "dering": ["✅ *{word_de}* \u2014 верно.", "✅ Правильно. *{word_de}*"],
    "imperator": ["✅ *{word_de}*."],
}

PRACTICE_WRONG = {
    "vitali": ["❌ Не совсем! Правильно: *{word_de}*\n💬 _{example}_", "❌ Почти! Правильный ответ: *{word_de}*\n_{example}_"],
    "dering": ["❌ Ошибка. Правильно: *{word_de}* \u2014 _{example}_"],
    "imperator": ["❌ *{word_de}*. _{example}_"],
}

PRACTICE_NEXT = {
    "vitali": "💪 Следующее! Напиши по-немецки: *{word_ru}*",
    "dering": "📝 Следующее. Переведите: *{word_ru}*",
    "imperator": "❗ *{word_ru}*:",
}

PRACTICE_DONE = {
    "vitali": "🎉 Отлично! Ты прошла все слова! Теперь закрепим: /quiz — или продолжим чат! 😊",
    "dering": "Упражнение завершено. Для закрепления: /quiz",
    "imperator": "Упражнение завершено. /quiz — если готова.",
}


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    settings = context.bot_data.get("settings")
    user = update.effective_user

    # --- Support-Codewort ---
    if settings and hasattr(settings, "support_codeword") and settings.support_codeword:
        if text.lower() == settings.support_codeword.lower():
            from bot.handlers.support import activate_support
            await activate_support(update, context)
            return

    if text.strip().lower() == "/endsupport":
        from bot.handlers.support import is_support_active, deactivate_support
        if is_support_active(context):
            await deactivate_support(update, context)
        return

    from bot.handlers.support import is_support_active, forward_to_admin
    if is_support_active(context) and settings and user.id == settings.authorized_user_id:
        await forward_to_admin(update, context)
        return

    if settings and user.id == settings.admin_user_id and user.id != settings.authorized_user_id:
        from bot.handlers.support import handle_admin_reply
        await handle_admin_reply(update, context)
        return

    # --- /skip Befehl während Übung ---
    if text.lower() in ("/skip", "skip"):
        await _handle_skip(update, context)
        return

    # --- Übungsphase: Antwort auf Vokabelübung ---
    session = get_session(context.user_data)
    if session.phase == LearningPhase.PRACTICE:
        await _handle_practice_answer(update, context, text, session)
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
            voice_id = voice_pipeline.voice_map.get(teacher.lower(), teacher)
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(response_text, voice_id)
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
    teacher = user_repo.get_teacher(user_id)

    word = session.current_practice_word()
    if not word:
        session.finish()
        return

    # Prüfen ob Antwort korrekt (case-insensitive, Artikel ignorieren)
    answer_clean = text.strip().lower().replace("der ", "").replace("die ", "").replace("das ", "")
    correct_clean = word["word_de"].lower().replace("der ", "").replace("die ", "").replace("das ", "")
    correct = answer_clean == correct_clean

    pool = PRACTICE_CORRECT[teacher] if correct else PRACTICE_WRONG[teacher]
    feedback = random.choice(pool).format(
        word_de=word["word_de"],
        example=word.get("example_de", ""),
    )
    await update.message.reply_text(feedback, parse_mode="Markdown")

    done = session.advance_practice(correct)

    if done:
        # Fortschritt speichern
        if lesson_planner and session.practice_results:
            lesson_planner.update_progress(user_id, session.practice_results)
        done_msg = PRACTICE_DONE.get(teacher, PRACTICE_DONE["vitali"])
        await update.message.reply_text(done_msg, parse_mode="Markdown")
        session.finish()
    else:
        next_word = session.current_practice_word()
        if next_word:
            msg = PRACTICE_NEXT.get(teacher, PRACTICE_NEXT["vitali"]).format(
                word_ru=next_word["word_ru"]
            )
            await update.message.reply_text(
                msg + "\n\n_(/skip чтобы пропустить)_",
                parse_mode="Markdown"
            )


async def _handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Springt zum nächsten Wort oder beendet Übung."""
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)

    session = get_session(context.user_data)
    if session.phase != LearningPhase.PRACTICE:
        await update.message.reply_text("Сейчас нет активной упражнения.")
        return

    done = session.advance_practice(False)
    if done:
        session.finish()
        done_msg = PRACTICE_DONE.get(teacher, PRACTICE_DONE["vitali"])
        await update.message.reply_text(done_msg, parse_mode="Markdown")
    else:
        next_word = session.current_practice_word()
        if next_word:
            msg = PRACTICE_NEXT.get(teacher, PRACTICE_NEXT["vitali"]).format(
                word_ru=next_word["word_ru"]
            )
            await update.message.reply_text(msg + "\n\n_(/skip чтобы пропустить)_", parse_mode="Markdown")
