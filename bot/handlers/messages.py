"""Text-Nachrichten Handler — natuerlicher Chat mit Imperator."""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.quiz import QUIZ_SESSION_KEY, handle_quiz
from services.session_manager import get_session, LearningPhase

logger = logging.getLogger(__name__)

PRACTICE_CORRECT = [
    "\u2705 *{word_de}*. \u041f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u043e.",
    "\u2705 *{word_de}*. \u0422\u043e\u0447\u043d\u043e.",
]
PRACTICE_WRONG = [
    "\u274c \u041d\u0435\u0442. *{word_de}*. \u0417\u0430\u043f\u043e\u043c\u043d\u0438.\n_{example}_",
    "\u274c \u0424\u0430\u043b\u044c\u0448\u043e. *{word_de}*.",
]
PRACTICE_CLOSE  = "\U0001f7e1 \u041f\u043e\u0447\u0442\u0438! \u041f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u043e: *{word_de}*. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439 \u0435\u0449\u0451 \u0440\u0430\u0437."
PRACTICE_NEXT   = "\u2757 *{word_ru}* \u2014 \u043f\u043e-\u043d\u0435\u043c\u0435\u0446\u043a\u0438:"
PRACTICE_DONE   = (
    "\U0001f525 \u0423\u043f\u0440\u0430\u0436\u043d\u0435\u043d\u0438\u0435 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043e.\n\n"
    "\u041c\u043e\u043b\u043e\u0434\u0435\u0446. \u0422\u0435\u043f\u0435\u0440\u044c /quiz \u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u044c \u043f\u0430\u043c\u044f\u0442\u044c. \u0418\u043b\u0438 \u043f\u0440\u043e\u0441\u0442\u043e \u043f\u0438\u0448\u0438 \u043c\u043d\u0435."
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
    if session.phase == LearningPhase.LESSON_ACTIVE and text.lower() in _PRACTICE_YES:
        session.start_practice()
        word = session.current_practice_word()
        if word:
            await update.message.reply_text(
                f"\U0001f525 \u041d\u0430\u0447\u0438\u043d\u0430\u0435\u043c!\n\n\u2757 *{word['word_ru']}* \u2014 \u043f\u043e-\u043d\u0435\u043c\u0435\u0446\u043a\u0438:"
                "\n\n_(/skip \u2014 \u043f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u0442\u044c)_",
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
        await update.message.reply_text("\u0421\u0435\u0440\u0432\u0438\u0441 \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d.")
        return

    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    await context.bot.send_chat_action(update.effective_chat.id, action="typing")

    try:
        result = await dialogue_router.generate_reply(user_id=user_id, user_text=text)
        reply  = result["text"] if isinstance(result, dict) else str(result)
    except Exception as e:
        logger.error("DialogueRouter error: %s", e, exc_info=True)
        reply = "\u041f\u0440\u043e\u0438\u0437\u043e\u0448\u043b\u0430 \u043e\u0448\u0438\u0431\u043a\u0430. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439 \u0435\u0449\u0451 \u0440\u0430\u0437."

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
        correct = False
    else:
        feedback = random.choice(PRACTICE_WRONG).format(
            word_de=word["word_de"], example=word.get("example_de", "")
        )
        correct = False

    await update.message.reply_text(feedback, parse_mode="Markdown")

    # Bei Typo: Wort NICHT weiterspringen
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
        await update.message.reply_text("\u0421\u0435\u0439\u0447\u0430\u0441 \u043d\u0435\u0442 \u0430\u043a\u0442\u0438\u0432\u043d\u043e\u0433\u043e \u0443\u043f\u0440\u0430\u0436\u043d\u0435\u043d\u0438\u044f.")
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
