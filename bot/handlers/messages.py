"""Text-Nachrichten Handler — natuerlicher Chat mit Imperator + Rollenspiel-Routing."""
from __future__ import annotations

import logging
import random
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.quiz import QUIZ_SESSION_KEY, handle_quiz
from services.session_manager import get_session, LearningPhase

logger = logging.getLogger(__name__)

PRACTICE_CORRECT = [
    "✅ *{word_de}*. Правильно.",
    "✅ *{word_de}*. Точно.",
]
PRACTICE_WRONG = [
    "❌ Нет. *{word_de}*. Запомни.\n_{example}_",
    "❌ Фальшиво. *{word_de}*.",
]
PRACTICE_CLOSE  = "🟡 Почти! Правильно: *{word_de}*. Попробуй ещё раз."
PRACTICE_NEXT   = "❗ *{word_ru}* — по-немецки:"
PRACTICE_DONE   = (
    "🔥 Упражнение завершено.\n\n"
    "Молодец. Теперь /quiz — проверь память. Или просто пиши мне."
)

_PRACTICE_YES = {"да", "yes", "ja", "ok", "давай", "хочу", "поехали", "go", "start"}

_FUZZY_RATIO = 0.25


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(
                prev[j] + 1,
                curr[j - 1] + 1,
                prev[j - 1] + (0 if ca == cb else 1)
            ))
        prev = curr
    return prev[-1]


def _is_close_enough(answer: str, correct: str) -> tuple[bool, bool]:
    a = answer.strip().lower()
    c = correct.strip().lower()
    for art in ("der ", "die ", "das ", "ein ", "eine "):
        a = a.removeprefix(art)
        c = c.removeprefix(art)
    if a == c:
        return True, True
    dist = _levenshtein(a, c)
    threshold = max(1, int(len(c) * _FUZZY_RATIO))
    return False, dist <= threshold


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text     = (update.message.text or "").strip()
    settings = context.bot_data.get("settings")
    user     = update.effective_user

    # Support-Modus
    from bot.handlers.support import is_support_active
    if settings and getattr(settings, "support_codeword", None):
        if user.id == settings.authorized_user_id and text.lower() == settings.support_codeword.lower():
            from bot.handlers.support import activate_support
            await activate_support(update, context)
            return

    if text.strip().lower() == "/endsupport":
        if is_support_active(context):
            from bot.handlers.support import deactivate_support
            await deactivate_support(update, context)
        return

    if is_support_active(context) and settings and user.id == settings.authorized_user_id:
        from bot.handlers.support import forward_to_admin
        await forward_to_admin(update, context)
        return

    if (settings and user.id == settings.admin_user_id
            and user.id != settings.authorized_user_id and is_support_active(context)):
        from bot.handlers.support import handle_admin_reply
        await handle_admin_reply(update, context)
        return

    if text.lower() in ("/skip", "skip"):
        await _handle_skip(update, context)
        return

    session = get_session(context.user_data)
    if session.phase == LearningPhase.PRACTICE:
        await _handle_practice_answer(update, context, text, session)
        return

    if session.phase == LearningPhase.LESSON_ACTIVE and text.lower() in _PRACTICE_YES:
        session.start_practice()
        word = session.current_practice_word()
        if word:
            await update.message.reply_text(
                f"🔥 Начинаем!\n\n❗ *{word['word_ru']}* — по-немецки:"
                "\n\n_(/skip — пропустить)_",
                parse_mode="Markdown"
            )
        return

    if context.user_data.get(QUIZ_SESSION_KEY) and text in {"1", "2", "3", "4"}:
        await handle_quiz(update, context)
        return

    # --- Rollenspiel aktiv? → extra_context injizieren ---
    services        = context.bot_data.get("services", {})
    dialogue_router = services.get("dialogue_router")
    tts             = services.get("tts")
    vp              = services.get("voice_pipeline")
    user_repo       = services.get("user_repo")

    if not dialogue_router or not user_repo:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    await context.bot.send_chat_action(update.effective_chat.id, action="typing")

    # Rollenspiel-Kontext bauen
    extra_ctx = ""
    current_rp = context.user_data.get("current_roleplay")
    if current_rp:
        is_explicit = context.user_data.get("flirt_mode", False)
        level = user_repo.get_level(user_id) or "a1"
        from bot.handlers.roleplay import get_rp_system_addon
        extra_ctx = get_rp_system_addon(current_rp, level, is_explicit)

    try:
        result = await dialogue_router.generate_reply(
            user_id=user_id,
            user_text=text,
            extra_context=extra_ctx,
        )
        reply  = result["text"] if isinstance(result, dict) else str(result)
    except Exception as e:
        logger.error("DialogueRouter error: %s", e, exc_info=True)
        reply = "Произошла ошибка. Попробуй ещё раз."

    await update.message.reply_text(reply)

    # TTS für Rollenspiel-Antworten
    if tts and vp and vp.voice_id:
        try:
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            af = await tts.synthesize(reply, vp.voice_id)
            with open(str(af), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS failed: %s", e)


async def _handle_practice_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, session
) -> None:
    services       = context.bot_data.get("services", {})
    user_repo      = services.get("user_repo")
    lesson_planner = services.get("lesson_planner")
    user    = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    word = session.current_practice_word()
    if not word:
        session.finish()
        return

    exact, close = _is_close_enough(text, word["word_de"])

    if exact:
        feedback = random.choice(PRACTICE_CORRECT).format(
            word_de=word["word_de"], example=word.get("example_de", "")
        )
        correct = True
    elif close:
        feedback = PRACTICE_CLOSE.format(word_de=word["word_de"])
        correct = False
    else:
        feedback = random.choice(PRACTICE_WRONG).format(
            word_de=word["word_de"], example=word.get("example_de", "")
        )
        correct = False

    await update.message.reply_text(feedback, parse_mode="Markdown")

    if close and not exact:
        return

    done = session.advance_practice(correct)

    if done:
        if lesson_planner and session.practice_results:
            lesson_planner.update_progress(user_id, session.practice_results)
        session.finish()
        await update.message.reply_text(PRACTICE_DONE, parse_mode="Markdown")
    else:
        nw = session.current_practice_word()
        if nw:
            await update.message.reply_text(
                f"{PRACTICE_NEXT.format(word_ru=nw['word_ru'])}\n\n_(/skip)_",
                parse_mode="Markdown"
            )


async def _handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = get_session(context.user_data)
    if session.phase != LearningPhase.PRACTICE:
        await update.message.reply_text("Сейчас нет активного упражнения.")
        return
    done = session.advance_practice(False)
    if done:
        session.finish()
        await update.message.reply_text(PRACTICE_DONE, parse_mode="Markdown")
    else:
        nw = session.current_practice_word()
        if nw:
            await update.message.reply_text(
                f"{PRACTICE_NEXT.format(word_ru=nw['word_ru'])}\n\n_(/skip)_",
                parse_mode="Markdown"
            )
