"""Handler fuer /lesson - startet eine Vokabel-Lerneinheit mit Session-Management."""
from __future__ import annotations

import io
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

TEACHER_LESSON_INTRO = {
    "vitali": "\U0001f4da Отлично, начинаем! Сегодня *{count} слов*. \nЧитай, запоминай, потом потренируемся!\n\n",
    "dering": "\U0001f4d6 Урок начат. *{count} единиц*. Внимание на примеры.\n\n",
    "imperator": "\U0001f525 *{count}* слов. Читай. Запоминай.\n\n",
}

TEACHER_LESSON_EMPTY = {
    "vitali": "\U0001f389 Наташа, ты уже выучила все доступные слова! Скоро добавим новые.",
    "dering": "Словарный запас текущего уровня исчерпан. Ожидайте пополнения.",
    "imperator": "Все слова изучены. Хорошо.",
}


def _format_step(step, i: int, total: int) -> str:
    icon = "\U0001f504" if step.type == "review_vocab" else "\u2728"
    tag = "(повторение)" if step.type == "review_vocab" else "(новое)"
    return (
        f"{icon} *{i}/{total}* {tag}\n"
        f"\U0001f1e9\U0001f1ea *{step.word_de}* \u2014 {step.word_ru}\n"
        f"\U0001f4ac _{step.example_de}_\n"
        f"\U0001f4dd {step.example_ru}"
    )


async def handle_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    lesson_planner = services.get("lesson_planner")
    tts = services.get("tts")
    voice_pipeline = services.get("voice_pipeline")

    if not lesson_planner or not user_repo:
        await update.message.reply_text("Сервис обучения временно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)

    args = context.args
    topic = args[0].lower() if args else None
    steps = lesson_planner.next_steps(user_id, topic=topic)

    if not steps:
        msg = TEACHER_LESSON_EMPTY.get(teacher, TEACHER_LESSON_EMPTY["vitali"])
        await update.message.reply_text(msg)
        return

    # Intro + Vokabeln - genau EIN reply_text
    intro = TEACHER_LESSON_INTRO.get(teacher, TEACHER_LESSON_INTRO["vitali"]).format(count=len(steps))
    lines = [intro]
    for i, step in enumerate(steps, 1):
        lines.append(_format_step(step, i, len(steps)))
        lines.append("")
    full_text = "\n".join(lines)
    await update.message.reply_text(full_text, parse_mode="Markdown")

    # Session starten - nur wenn user_data ein echtes dict ist
    user_data = context.user_data
    settings = context.bot_data.get("settings")
    if settings and isinstance(user_data, dict):
        try:
            from services.session_manager import get_session
            session = get_session(user_data)
            session.start_lesson([
                {"vocab_id": s.vocab_id, "word_de": s.word_de, "word_ru": s.word_ru, "example_de": s.example_de}
                for s in steps
            ])
        except Exception as e:
            logger.warning("Session init failed: %s", e)

    # Lernkarten als Bilder
    try:
        from services.card_generator import generate_card_bytes
        for i, step in enumerate(steps, 1):
            card_bytes = generate_card_bytes(
                word_de=step.word_de, word_ru=step.word_ru,
                example=step.example_de, card_num=i, teacher=teacher,
            )
            if card_bytes:
                await update.message.reply_photo(
                    photo=io.BytesIO(card_bytes),
                    caption=f"{step.word_de} = {step.word_ru}",
                )
    except Exception as e:
        logger.warning("Card generation failed: %s", e)

    # TTS
    if tts and voice_pipeline:
        words_de = ", ".join(s.word_de for s in steps)
        tts_text = f"Heute lernst du: {words_de}."
        try:
            voice_id = voice_pipeline.voice_map.get(teacher.lower(), teacher)
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(tts_text, voice_id)
            with open(str(audio_file), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS for lesson failed: %s", e)

    # Nach Lektion: Uebung starten (nur wenn settings und echtes user_data)
    if settings and isinstance(user_data, dict):
        try:
            from services.session_manager import get_session
            session = get_session(user_data)
            await _start_practice(update, context, teacher, session)
        except Exception as e:
            logger.warning("Practice start failed: %s", e)


async def _start_practice(
    update: Update, context: ContextTypes.DEFAULT_TYPE, teacher: str, session
) -> None:
    """Startet die Uebungsphase direkt nach der Lektion."""
    session.start_practice()
    word = session.current_practice_word()
    if not word:
        return

    intros = {
        "vitali": f"\U0001f4aa Теперь проверим! Напиши по-немецки: *{word['word_ru']}*",
        "dering": f"\U0001f4dd Переведите: *{word['word_ru']}*",
        "imperator": f"\u2757 *{word['word_ru']}* \u2014 по-немецки:",
    }
    msg = intros.get(teacher, intros["vitali"])
    await update.message.reply_text(
        msg + "\n\n_(напиши ответ или /skip чтобы пропустить)_",
        parse_mode="Markdown"
    )
