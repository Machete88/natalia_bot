"""Handler fuer /lesson - startet eine Vokabel-Lerneinheit mit Session-Management."""
from __future__ import annotations

import io
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

TEACHER_LESSON_INTRO = {
    "vitali": "\U0001f4da \u041e\u0442\u043b\u0438\u0447\u043d\u043e, \u043d\u0430\u0447\u0438\u043d\u0430\u0435\u043c! \u0421\u0435\u0433\u043e\u0434\u043d\u044f *{count} \u0441\u043b\u043e\u0432*. \n\u0427\u0438\u0442\u0430\u0439, \u0437\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u0439, \u043f\u043e\u0442\u043e\u043c \u043f\u043e\u0442\u0440\u0435\u043d\u0438\u0440\u0443\u0435\u043c\u0441\u044f!\n\n",
    "dering": "\U0001f4d6 \u0423\u0440\u043e\u043a \u043d\u0430\u0447\u0430\u0442. *{count} \u0435\u0434\u0438\u043d\u0438\u0446*. \u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435 \u043d\u0430 \u043f\u0440\u0438\u043c\u0435\u0440\u044b.\n\n",
    "imperator": "\U0001f525 *{count}* \u0441\u043b\u043e\u0432. \u0427\u0438\u0442\u0430\u0439. \u0417\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u0439.\n\n",
}

TEACHER_LESSON_EMPTY = {
    "vitali": "\U0001f389 \u041d\u0430\u0442\u0430\u0448\u0430, \u0442\u044b \u0443\u0436\u0435 \u0432\u044b\u0443\u0447\u0438\u043b\u0430 \u0432\u0441\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0435 \u0441\u043b\u043e\u0432\u0430! \u0421\u043a\u043e\u0440\u043e \u0434\u043e\u0431\u0430\u0432\u0438\u043c \u043d\u043e\u0432\u044b\u0435.",
    "dering": "\u0421\u043b\u043e\u0432\u0430\u0440\u043d\u044b\u0439 \u0437\u0430\u043f\u0430\u0441 \u0442\u0435\u043a\u0443\u0449\u0435\u0433\u043e \u0443\u0440\u043e\u0432\u043d\u044f \u0438\u0441\u0447\u0435\u0440\u043f\u0430\u043d. \u041e\u0436\u0438\u0434\u0430\u0439\u0442\u0435 \u043f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f.",
    "imperator": "\u0412\u0441\u0435 \u0441\u043b\u043e\u0432\u0430 \u0438\u0437\u0443\u0447\u0435\u043d\u044b. \u0425\u043e\u0440\u043e\u0448\u043e.",
}


def _format_step(step, i: int, total: int) -> str:
    icon = "\U0001f504" if step.type == "review_vocab" else "\u2728"
    tag = "(\u043f\u043e\u0432\u0442\u043e\u0440\u0435\u043d\u0438\u0435)" if step.type == "review_vocab" else "(\u043d\u043e\u0432\u043e\u0435)"
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
        await update.message.reply_text("\u0421\u0435\u0440\u0432\u0438\u0441 \u043e\u0431\u0443\u0447\u0435\u043d\u0438\u044f \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d.")
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

    # Genau EIN reply_text mit allen Vokabeln
    intro = TEACHER_LESSON_INTRO.get(teacher, TEACHER_LESSON_INTRO["vitali"]).format(count=len(steps))
    lines = [intro]
    for i, step in enumerate(steps, 1):
        lines.append(_format_step(step, i, len(steps)))
        lines.append("")
    full_text = "\n".join(lines)
    await update.message.reply_text(full_text, parse_mode="Markdown")

    # Alle weiteren Aktionen nur mit echtem settings-Objekt (nicht im Test-Pfad)
    settings = context.bot_data.get("settings")
    user_data = context.user_data

    if settings and isinstance(user_data, dict):
        # Session starten
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

        # Nach Lektion: Uebung starten
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
        "vitali": f"\U0001f4aa \u0422\u0435\u043f\u0435\u0440\u044c \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u043c! \u041d\u0430\u043f\u0438\u0448\u0438 \u043f\u043e-\u043d\u0435\u043c\u0435\u0446\u043a\u0438: *{word['word_ru']}*",
        "dering": f"\U0001f4dd \u041f\u0435\u0440\u0435\u0432\u0435\u0434\u0438\u0442\u0435: *{word['word_ru']}*",
        "imperator": f"\u2757 *{word['word_ru']}* \u2014 \u043f\u043e-\u043d\u0435\u043c\u0435\u0446\u043a\u0438:",
    }
    msg = intros.get(teacher, intros["vitali"])
    await update.message.reply_text(
        msg + "\n\n_(\u043d\u0430\u043f\u0438\u0448\u0438 \u043e\u0442\u0432\u0435\u0442 \u0438\u043b\u0438 /skip \u0447\u0442\u043e\u0431\u044b \u043f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u0442\u044c)_",
        parse_mode="Markdown"
    )
