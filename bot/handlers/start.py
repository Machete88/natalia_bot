"""Handler for /start command — Imperator only."""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

WELCOME = (
    "\U0001f525 *Я Император.*\n\n"
    "Немецкий \u2014 это не просто слова. Это другой способ видеть мир. Готова?"
)

PLAN_TEXT = """
\U0001f4cb *План обучения:*

\U0001f4da /lesson \u2014 учим 5 новых слов
\U0001f914 /quiz \u2014 викторина: угадай слово
\U0001f4ca /progress \u2014 твой прогресс
\U0001f4d0 /setlevel a1 \u2014 установить уровень
\U0001f3a4 Голос \u2014 говори со мной по-немецки
\U0001f4f8 Фото \u2014 проверка домашней работы
\U0001f4ac Пиши \u2014 просто напиши мне. Отвечу.

_Начнём? Напиши *Hallo* или отправь голосовое._
"""


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    tts = services.get("tts")
    voice_pipeline = services.get("voice_pipeline")
    sticker_service = services.get("sticker_service")

    user = update.effective_user
    if user_repo:
        user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
        user_repo.set_teacher(user_id, "imperator")

    full_msg = f"{WELCOME}\n{PLAN_TEXT}"
    await update.message.reply_text(full_msg, parse_mode="Markdown")

    # Sticker
    if sticker_service:
        sticker_id = sticker_service.get_sticker_for_event("greeting")
        if sticker_id:
            try:
                await update.message.reply_sticker(sticker_id)
            except Exception as e:
                logger.debug("Sticker send failed: %s", e)

    # Begruessung als Sprachnachricht
    greeting_tts = (
        "Я Император. Немецкий \u2014 это другой способ видеть мир. Готова?"
    )
    if tts and voice_pipeline and voice_pipeline.voice_id:
        try:
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            audio_file = await tts.synthesize(greeting_tts, voice_pipeline.voice_id)
            with open(str(audio_file), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS for start greeting failed: %s", e)
