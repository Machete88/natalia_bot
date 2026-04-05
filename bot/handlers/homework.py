"""Handler fuer Hausaufgaben: Foto oder Dokument -> OCR -> Lehrer-Korrektur per Voice."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

HOMEWORK_DIR = Path("media/homework")
HOMEWORK_DIR.mkdir(parents=True, exist_ok=True)

# Einfaches OCR: liest Bildtext mit pytesseract, falls verfuegbar, sonst Fallback
async def _extract_text(file_path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img, lang="deu+rus")
        return text.strip()
    except ImportError:
        return "[OCR nicht verfuegbar - pytesseract/Pillow nicht installiert]"
    except Exception as e:
        logger.warning("OCR failed: %s", e)
        return f"[OCR-Fehler: {e}]"


def _save_submission(db_path: str, user_id: int, file_path: str, extracted_text: str) -> int:
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO homework_submissions (user_id, file_path, extracted_text)
            VALUES (?, ?, ?)
            """,
            (user_id, file_path, extracted_text),
        )
        return cur.lastrowid


def _build_correction_prompt(teacher_persona: str, extracted_text: str) -> str:
    return (
        f"{teacher_persona}\n\n"
        "Наталья прислала фото своей домашней работы. "
        "Вот распознанный текст:\n"
        f"\"\"\"\n{extracted_text}\n\"\"\"\n\n"
        "Проверь этот текст как учитель немецкого: найди ошибки, объясни их коротко по-русски, "
        "дай правильный вариант. Если текст нечитаем или слишком короткий, скажи об этом. "
        "Ответ кратко, по-русски."
    )


TEACHER_PERSONAS = {
    "dering": (
        "Ты — учитель немецкого языка по имени Деринг. Ты старый, строгий, структурированный, "
        "немного старомодный, но добросовестный. Говоришь кратко, по делу, без лишних эмоций. "
        "Всегда на русском языке, немецкие примеры выделяй."
    ),
    "vitali": (
        "Ты — учитель немецкого языка по имени Витали. Ты тёплый, живой, с юмором. "
        "Говоришь как друг, которому важно, чтобы Наталья учила язык с удовольствием. "
        "Короткие живые фразы на русском, немецкий — как приятное открытие."
    ),
    "imperator": (
        "Ты — учитель немецкого языка по имени Император. Ты спокойный, наблюдательный, "
        "магнетичный. Каждое слово весомо. Говоришь как человек, который замечает всё. "
        "Эмоционально насыщенно, но без пошлости. Ответы на русском, очень точные."
    ),
}

RECEIVED_MESSAGES = {
    "vitali": "\U0001f4f8 Отлично, Наташа! Получила твою домашнюю работу, сейчас проверю... \U0001f50d",
    "dering": "Домашняя работа получена. Приступаю к проверке.",
    "imperator": "\U0001f4f8 Получено. Проверяю.",
}


async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verarbeitet Fotos oder Dokumente als Hausaufgaben."""
    services = context.bot_data.get("services", {})
    settings = context.bot_data.get("settings")
    user_repo = services.get("user_repo")
    dialogue_router = services.get("dialogue_router")
    tts = services.get("tts")
    voice_pipeline = services.get("voice_pipeline")

    if not user_repo or not dialogue_router or not settings:
        await update.message.reply_text("Сервис временно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)

    # Bestaetigungsmeldung sofort senden
    received_msg = RECEIVED_MESSAGES.get(teacher, RECEIVED_MESSAGES["vitali"])
    await update.message.reply_text(received_msg)
    await context.bot.send_chat_action(update.effective_chat.id, action="typing")

    # Datei herunterladen
    try:
        if update.message.photo:
            # Groesstmoegliches Foto nehmen
            tg_file_obj = await context.bot.get_file(update.message.photo[-1].file_id)
            file_unique = update.message.photo[-1].file_unique_id
            suffix = ".jpg"
        elif update.message.document:
            tg_file_obj = await context.bot.get_file(update.message.document.file_id)
            file_unique = update.message.document.file_unique_id
            orig_name = update.message.document.file_name or "doc"
            suffix = Path(orig_name).suffix or ".bin"
        else:
            await update.message.reply_text("Пришли фото или документ с домашней работой.")
            return

        local_path = HOMEWORK_DIR / f"hw_{user_id}_{file_unique}{suffix}"
        await tg_file_obj.download_to_drive(str(local_path))
    except Exception as e:
        logger.error("Homework download failed: %s", e, exc_info=True)
        await update.message.reply_text("Не удалось загрузить файл. Попробуй ещё раз.")
        return

    # OCR
    await context.bot.send_chat_action(update.effective_chat.id, action="typing")
    extracted = await _extract_text(local_path)

    # In DB speichern
    try:
        _save_submission(settings.database_path, user_id, str(local_path), extracted)
    except Exception as e:
        logger.warning("Could not save homework submission: %s", e)

    # LLM-Korrektur
    persona = TEACHER_PERSONAS.get(teacher, TEACHER_PERSONAS["vitali"])
    correction_prompt = _build_correction_prompt(persona, extracted)

    try:
        correction_text = await dialogue_router._llm.complete(correction_prompt)
    except Exception as e:
        logger.error("LLM correction failed: %s", e, exc_info=True)
        correction_text = "Извини, не смогла обработать домашнюю работу. Попробуй позже."

    # Antwort: Text + Voice
    await update.message.reply_text(correction_text)

    if tts and voice_pipeline:
        try:
            voice_map = voice_pipeline.voice_map
            voice_id = voice_map.get(teacher.lower(), teacher)
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(correction_text, voice_id)
            with open(str(audio_file), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS for homework failed: %s", e)
