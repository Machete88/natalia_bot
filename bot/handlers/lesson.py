"""Handler fuer /lesson — Vokabeln zeigen, KEINE sofortige Abfrage."""
from __future__ import annotations

import io
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

LESSON_EMPTY = (
    "\U0001f525 Все слова на этом уровне выучены.\n\n"
    "_Попробуй /quiz \u2014 проверь память._"
)

LESSON_INTRO = (
    "\U0001f525 *Сегодня {count} слов.* Читай, слушай, запоминай.\n\n"
    "_Когда будешь готова \u2014 /quiz._"
)

PRACTICE_PROMPT = (
    "\n\n\U0001f4ac _Хочешь сразу потренироваться?_ Напиши *да* или иди дальше."
)


def _format_word(step, i: int, total: int) -> str:
    icon = "\U0001f504" if step.type == "review_vocab" else "\u2728"
    tag  = "(Повторение)" if step.type == "review_vocab" else "(Новое)"
    return (
        f"{icon} *{i}/{total}* {tag}\n"
        f"\U0001f1e9\U0001f1ea *{step.word_de}* \u2014 {step.word_ru}\n"
        f"\U0001f4ac _{step.example_de}_\n"
        f"\U0001f4dd {step.example_ru}"
    )


async def handle_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services      = context.bot_data.get("services", {})
    user_repo     = services.get("user_repo")
    lesson_planner= services.get("lesson_planner")
    tts           = services.get("tts")
    vp            = services.get("voice_pipeline")

    if not lesson_planner or not user_repo:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user    = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    args  = context.args
    topic = args[0].lower() if args else None
    steps = lesson_planner.next_steps(user_id, topic=topic)

    if not steps:
        await update.message.reply_text(LESSON_EMPTY, parse_mode="Markdown")
        return

    # Alle Wörter in EINER Nachricht zeigen
    intro = LESSON_INTRO.format(count=len(steps))
    cards: list[str] = []
    for i, s in enumerate(steps, 1):
        cards.append(_format_word(s, i, len(steps)))
    body = "\n\n".join(cards)
    await update.message.reply_text(
        f"{intro}\n\n{body}{PRACTICE_PROMPT}",
        parse_mode="Markdown"
    )

    # Session speichern für spätere Practice
    settings = context.bot_data.get("settings")
    if settings and isinstance(context.user_data, dict):
        try:
            from services.session_manager import get_session
            session = get_session(context.user_data)
            session.start_lesson([
                {"vocab_id": s.vocab_id, "word_de": s.word_de,
                 "word_ru": s.word_ru, "example_de": s.example_de}
                for s in steps
            ])
        except Exception as e:
            logger.warning("Session init failed: %s", e)

    # Vocab-Karten als Bilder
    try:
        from services.card_generator import generate_card_bytes
        for i, step in enumerate(steps, 1):
            cb = generate_card_bytes(
                word_de=step.word_de, word_ru=step.word_ru,
                example=step.example_de, card_num=i, teacher="imperator",
            )
            if cb:
                await update.message.reply_photo(
                    photo=io.BytesIO(cb),
                    caption=f"{step.word_de} = {step.word_ru}",
                )
    except Exception as e:
        logger.debug("Card generation: %s", e)

    # TTS: alle Wörter vorlesen
    if tts and vp and vp.voice_id:
        words_de = ", ".join(s.word_de for s in steps)
        tts_text = f"Сегодня мы учим: {words_de}."
        try:
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            af = await tts.synthesize(tts_text, vp.voice_id)
            with open(str(af), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS lesson failed: %s", e)

    # KEIN automatischer Practice-Start — Natasha entscheidet selbst
