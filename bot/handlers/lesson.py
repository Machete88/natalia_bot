"""Handler fuer /lesson Befehl - startet eine Vokabel-Lerneinheit."""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

TEACHER_LESSON_INTRO = {
    "vitali": (
        "\U0001f4da Отлично, начинаем учиться! Сегодня у нас {count} слов.\n"
        "Я покажу тебе слово и пример — просто читай и запоминай!\n\n"
    ),
    "dering": (
        "\U0001f4d6 Урок начат. {count} лексических единиц для изучения.\n"
        "Внимание на примеры.\n\n"
    ),
    "imperator": (
        "\U0001f525 {count} слов. Читай. Запоминай. Это важно.\n\n"
    ),
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
        f"\U0001f1e9\U0001f1ea *{step.word_de}* — {step.word_ru}\n"
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

    # Optionaler Topic-Parameter: /lesson feelings
    args = context.args
    topic = args[0].lower() if args else None

    steps = lesson_planner.next_steps(user_id, topic=topic)

    if not steps:
        msg = TEACHER_LESSON_EMPTY.get(teacher, TEACHER_LESSON_EMPTY["vitali"])
        await update.message.reply_text(msg)
        return

    # Intro-Nachricht
    intro = TEACHER_LESSON_INTRO.get(teacher, TEACHER_LESSON_INTRO["vitali"]).format(
        count=len(steps)
    )

    # Alle Vokabeln als eine Nachricht zusammenbauen
    lines = [intro]
    for i, step in enumerate(steps, 1):
        lines.append(_format_step(step, i, len(steps)))
        lines.append("")  # Leerzeile zwischen Eintraegen

    full_text = "\n".join(lines)

    # Text als Telegram-Nachricht senden (Markdown)
    await update.message.reply_text(full_text, parse_mode="Markdown")

    # Zusaetzlich: TTS-Zusammenfassung der deutschen Woerter
    if tts and voice_pipeline:
        words_de = ", ".join(step.word_de for step in steps)
        tts_text = f"Heute lernst du: {words_de}."

        try:
            voice_map = voice_pipeline.voice_map
            voice_id = voice_map.get(teacher.lower(), teacher)
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(tts_text, voice_id)
            with open(str(audio_file), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS for lesson failed: %s", e)
