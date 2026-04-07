"""Voice message handler: STT → Sprachbefehl-Erkennung → DialogueRouter → TTS."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sprachbefehl-Erkennung
# ---------------------------------------------------------------------------
_VOICE_COMMANDS: list[tuple[list[str], str]] = [
    (["урок", "лексику", "лексика", "словa", "слова", "учить", "lektion", "lesson", "вокабуляр"], "lesson"),
    (["квиз", "тест", "проверь", "проверка", "quiz", "тестируй"], "quiz"),
    (["прогресс", "статистика", "статистику", "мой прогресс", "progress"], "progress"),
    (["учитель", "смени учителя", "другой учитель", "teacher", "император", "imperator"], "teacher"),
    (["уровень", "мой уровень", "setlevel", "level", "a1", "a2", "b1", "b2", "c1"], "setlevel"),
    (["напомни", "напоминание", "remind", "erinnerung"], "remind"),
]

_TOPIC_MAP: list[tuple[list[str], str]] = [
    (["еда", "еду", "пить", "питье", "ресторан", "кухня", "essen", "food", "trinken"], "food"),
    (["цвета", "цветы", "оттенки", "farben", "farbe", "colors"], "colors"),
    (["числа", "цифры", "считать", "zahlen", "numbers", "zahl"], "numbers"),
    (["время", "день", "неделя", "месяц", "zeit", "datum", "uhrzeit", "woche"], "time"),
    (["семья", "родственники", "родители", "familie", "family"], "family"),
    (["тело", "здоровье", "части тела", "körper", "gesundheit", "body"], "body"),
    (["путешествие", "поездка", "отпуск", "reise", "travel", "urlaub"], "travel"),
    (["работа", "профессия", "офис", "arbeit", "beruf", "job", "work"], "work"),
    (["дом", "квартира", "комната", "haus", "wohnen", "zimmer", "wohnung"], "home"),
    (["погода", "погоду", "wetter", "weather", "regen", "sonne"], "weather"),
    (["магазин", "покупки", "одежда", "einkaufen", "shopping", "kleidung"], "shopping"),
    (["чувства", "эмоции", "настроение", "gefühle", "emotionen", "feelings"], "feelings"),
    (["животные", "питомцы", "tiere", "animals", "haustiere"], "animals"),
]


def _detect_voice_command(text: str) -> str | None:
    lower = text.lower()
    for keywords, cmd in _VOICE_COMMANDS:
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', lower):
                return cmd
    return None


def _detect_topic(text: str) -> str | None:
    lower = text.lower()
    for keywords, topic in _TOPIC_MAP:
        for kw in keywords:
            if kw in lower:
                return topic
    return None


def _extract_level_arg(text: str) -> str | None:
    lower = text.lower()
    for lvl in ["c1", "b2", "b1", "a2", "a1", "beginner"]:
        if lvl in lower:
            return lvl
    return None


async def _dispatch_voice_command(
    cmd: str, text: str, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if cmd == "lesson":
        topic = _detect_topic(text)
        context.args = [topic] if topic else []
        from bot.handlers.lesson import handle_lesson
        await handle_lesson(update, context)

    elif cmd == "quiz":
        from bot.handlers.quiz import handle_quiz
        await handle_quiz(update, context)

    elif cmd == "progress":
        from bot.handlers.progress import handle_progress
        await handle_progress(update, context)

    elif cmd == "teacher":
        # Always imperator — just confirm
        context.args = ["imperator"]
        from bot.handlers.teacher import handle_teacher
        await handle_teacher(update, context)

    elif cmd == "setlevel":
        arg = _extract_level_arg(text)
        context.args = [arg] if arg else []
        from bot.handlers.setlevel import handle_setlevel
        await handle_setlevel(update, context)

    elif cmd == "remind":
        await update.message.reply_text(
            "\u23f0 Nutze /remind 09:00 um eine tägliche Erinnerung zu setzen, "
            "oder /remind off zum Deaktivieren."
        )


# ---------------------------------------------------------------------------
# Haupt-Handler
# ---------------------------------------------------------------------------
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from bot.handlers.pronunciation import handle_voice_pronunciation
    handled = await handle_voice_pronunciation(update, context)
    if handled:
        return

    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    voice_pipeline = services.get("voice_pipeline")
    dialogue_router = services.get("dialogue_router")
    tts = services.get("tts")
    stt = services.get("stt")

    if not user_repo or not voice_pipeline:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")

    await context.bot.send_chat_action(update.effective_chat.id, action="typing")

    # Audio herunterladen
    try:
        tg_file = await context.bot.get_file(update.message.voice.file_id)
        audio_dir = Path("media/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)
        local_path = audio_dir / f"voice_{user.id}_{update.message.voice.file_unique_id}.ogg"
        await tg_file.download_to_drive(str(local_path))
    except Exception as e:
        logger.error("Voice download failed: %s", e)
        await update.message.reply_text("Не удалось загрузить аудио.")
        return

    # STT
    try:
        text = await stt.transcribe(local_path)
    except Exception as e:
        logger.warning("STT failed: %s", e)
        text = ""

    if not text or not text.strip():
        await update.message.reply_text("Не удалось распознать речь. Попробуй ещё раз.")
        return

    await update.message.reply_text(f"📝 Распознано: _{text}_", parse_mode="Markdown")

    # Sprachbefehl erkennen (Priorität)
    cmd = _detect_voice_command(text)
    if cmd:
        logger.info("Voice command detected: %s (text: %s)", cmd, text)
        await _dispatch_voice_command(cmd, text, update, context)
        return

    # Normaler Dialogue-Router
    if not dialogue_router:
        return

    await context.bot.send_chat_action(update.effective_chat.id, action="typing")
    try:
        result = await dialogue_router.generate_reply(user_id=user_id, user_text=text)
        response_text = result["text"] if isinstance(result, dict) else str(result)
    except Exception as e:
        logger.error("DialogueRouter error: %s", e)
        response_text = "Извини, произошла ошибка."

    await update.message.reply_text(response_text)

    # TTS — always Imperator voice_id from pipeline
    if tts and voice_pipeline and voice_pipeline.voice_id:
        try:
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(response_text, voice_pipeline.voice_id)
            with open(str(audio_file), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS failed: %s", e)
