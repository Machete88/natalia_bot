"""Handler fuer /lesson — Herr Imperator erteilt den Befehl."""
from __future__ import annotations

import io
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

LESSON_EMPTY = (
    "\U0001f525 *Все слова этого уровня освоены.*\n\n"
    "_Господин Император доволен. Проверь себя: /quiz_"
)

LESSON_INTRO = (
    "\U0001f525 *Сегодня {count} слов по приказу Господина Императора.* "
    "Читай. Слушай. Запоминай.\n\n"
    "_Когда будешь готова — /quiz. Провалишься — пожалеешь._"
)

PRACTICE_PROMPT = (
    "\n\n\U0001f4ac _Хочешь потренироваться прямо сейчас?_ "
    "Напиши *да* — или Господин Император решит за тебя."
)

TOPIC_SELECT_MSG = "\U0001f4da Выбери тему — Господин Император ждёт:"
TOPIC_ALL_LABEL  = "\U0001f504 Повторение (все темы)"


def _format_word(step, i: int, total: int) -> str:
    icon = "\U0001f504" if step.type == "review_vocab" else "\u2728"
    tag  = "(Повторение)" if step.type == "review_vocab" else "(Новое)"
    return (
        f"{icon} *{i}/{total}* {tag}\n"
        f"\U0001f1e9\U0001f1ea *{step.word_de}* — {step.word_ru}\n"
        f"\U0001f4ac _{step.example_de}_\n"
        f"\U0001f4dd {step.example_ru}"
    )


def _topic_keyboard(topics: list[str]) -> InlineKeyboardMarkup:
    buttons = []
    row: list[InlineKeyboardButton] = []
    for t in topics:
        row.append(InlineKeyboardButton(t.capitalize(), callback_data=f"lesson_topic_{t}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(TOPIC_ALL_LABEL, callback_data="lesson_topic_all")])
    return InlineKeyboardMarkup(buttons)


async def handle_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services       = context.bot_data.get("services", {})
    user_repo      = services.get("user_repo")
    lesson_planner = services.get("lesson_planner")
    tts            = services.get("tts")
    vp             = services.get("voice_pipeline")

    if not lesson_planner or not user_repo:
        await update.message.reply_text("Господин Император временно недоступен.")
        return

    user    = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    args  = context.args
    topic = args[0].lower() if args else None

    if not topic:
        try:
            topics = lesson_planner.available_topics(user_id)
        except Exception:
            topics = []

        if topics and len(topics) > 1:
            kb = _topic_keyboard(topics)
            await update.message.reply_text(
                TOPIC_SELECT_MSG,
                reply_markup=kb,
                parse_mode="Markdown"
            )
            return
        topic = topics[0] if len(topics) == 1 else None

    await _deliver_lesson(update, context, user_id, topic, lesson_planner, tts, vp)


async def handle_lesson_topic_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str
) -> None:
    services       = context.bot_data.get("services", {})
    user_repo      = services.get("user_repo")
    lesson_planner = services.get("lesson_planner")
    tts            = services.get("tts")
    vp             = services.get("voice_pipeline")

    if not lesson_planner or not user_repo:
        await update.callback_query.answer("Господин Император недоступен.")
        return

    user    = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    chosen = None if topic == "all" else topic
    await update.callback_query.answer()
    await update.callback_query.edit_message_reply_markup(reply_markup=None)
    await _deliver_lesson(update, context, user_id, chosen, lesson_planner, tts, vp)


async def _deliver_lesson(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    topic: str | None,
    lesson_planner,
    tts,
    vp,
) -> None:
    steps = lesson_planner.next_steps(user_id, topic=topic)

    msg = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if not msg:
        return

    if not steps:
        await msg.reply_text(LESSON_EMPTY, parse_mode="Markdown")
        return

    intro = LESSON_INTRO.format(count=len(steps))
    cards = [_format_word(s, i, len(steps)) for i, s in enumerate(steps, 1)]
    body  = "\n\n".join(cards)
    await msg.reply_text(
        f"{intro}\n\n{body}{PRACTICE_PROMPT}",
        parse_mode="Markdown"
    )

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

    try:
        from services.card_generator import generate_card_bytes
        for i, step in enumerate(steps, 1):
            cb = generate_card_bytes(
                word_de=step.word_de, word_ru=step.word_ru,
                example=step.example_de, card_num=i, teacher="imperator",
            )
            if cb:
                await msg.reply_photo(
                    photo=io.BytesIO(cb),
                    caption=f"{step.word_de} = {step.word_ru}",
                )
    except Exception as e:
        logger.debug("Card generation: %s", e)

    if tts and vp and vp.voice_id:
        words_de = ", ".join(s.word_de for s in steps)
        tts_text = f"Господин Император приказывает выучить: {words_de}."
        try:
            await context.bot.send_chat_action(
                update.effective_chat.id, action="record_voice"
            )
            af = await tts.synthesize(tts_text, vp.voice_id)
            with open(str(af), "rb") as f:
                await msg.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS lesson failed: %s", e)
