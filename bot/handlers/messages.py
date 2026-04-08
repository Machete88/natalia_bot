"""Text-Nachrichten Handler — natuerlicher Chat mit Imperator."""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.quiz import QUIZ_SESSION_KEY, handle_quiz
from services.session_manager import get_session, LearningPhase

logger = logging.getLogger(__name__)

PRACTICE_CORRECT = [
    "\u2705 *{word_de}*. Правильно.",
    "\u2705 *{word_de}*. Точно.",
]
PRACTICE_WRONG = [
    "\u274c Нет. *{word_de}*. Запомни.\n_{example}_",
    "\u274c Фальшо. *{word_de}*.",
]
PRACTICE_CLOSE  = "\U0001f7e1 Почти! Правильно: *{word_de}*. Попробуй ещё раз."
PRACTICE_NEXT   = "\u2757 *{word_ru}* — по-немецки:"
PRACTICE_DONE   = (
    "\U0001f525 Упражнение завершено.\n\n"
    "Молодец. Теперь /quiz — проверь память. Или просто пиши мне."
)

_PRACTICE_YES = {"\u0434\u0430", "yes", "ja", "ok", "\u0434\u0430\u0432\u0430\u0439", "\u0445\u043e\u0447\u0443", "\u043f\u043e\u0435\u0445\u0430\u043b\u0438", "go", "start"}

# Fuzzy-Toleranz: max. Levenshtein-Distanz relativ zur Wortlaenge
_FUZZY_RATIO = 0.25  # 25% der Zeichen duerfen abweichen


def _levenshtein(a: str, b: str) -> int:
    """Berechnet Levenshtein-Distanz zwischen zwei Strings."""
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
    """Gibt (exakt_korrekt, fast_korrekt) zurueck."""
    a = answer.strip().lower()
    c = correct.strip().lower()
    # Artikel entfernen fuer Vergleich
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

    # /skip
    if text.lower() in ("/skip", "skip"):
        await _handle_skip(update, context)
        return

    # Practice laeuft
    session = get_session(context.user_data)
    if session.phase == LearningPhase.PRACTICE:
        await _handle_practice_answer(update, context, text, session)
        return

    # Natasha sagt "ja" nach Lesson
    if session.phase == LearningPhase.LESSON and text.lower() in _PRACTICE_YES:
        session.start_practice()
        word = session.current_practice_word()
        if word:
            await update.message.reply_text(
                f"\U0001f525 Начинаем!\n\n\u2757 *{word['word_ru']}* — по-немецки:"
                "\n\n_(/skip — пропустить)_",
                parse_mode="Markdown"
            )
        return

    # Quiz laeuft
    if context.user_data.get(QUIZ_SESSION_KEY) and text in {"1", "2", "3", "4"}:
        await handle_quiz(update, context)
        return

    # Normaler Chat mit Imperator
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

    try:
        result = await dialogue_router.generate_reply(user_id=user_id, user_text=text)
        reply  = result["text"] if isinstance(result, dict) else str(result)
    except Exception as e:
        logger.error("DialogueRouter error: %s", e, exc_info=True)
        reply = "Произошла ошибка. Попробуй ещё раз."

    await update.message.reply_text(reply)

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
    import random
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
        correct = False  # Typo zaehlt nicht als Erfolg fuer SM-2
    else:
        feedback = random.choice(PRACTICE_WRONG).format(
            word_de=word["word_de"], example=word.get("example_de", "")
        )
        correct = False

    await update.message.reply_text(feedback, parse_mode="Markdown")

    # Bei Typo: Wort NICHT weiterspringen — Natasha soll es nochmal versuchen
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
