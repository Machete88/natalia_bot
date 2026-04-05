"""Handler for /start command."""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

WELCOME_DERING = (
    "Добрый день. Я Деринг — ваш преподаватель немецкого языка. "
    "Мы начнём с основ. Напишите, что вас интересует, или просто скажите «Привет»."
)
WELCOME_VITALI = (
    "Привет, Наташа! 😊 Я Витали — твой учитель немецкого. "
    "Рад тебя видеть! Расскажи, как ты сегодня? А потом начнём учить что-нибудь интересное!"
)
WELCOME_IMPERATOR = (
    "Ты здесь. Хорошо. Я Император. "
    "Немецкий язык — это не просто слова. Это другой способ видеть мир. "
    "Готова начать?"
)

WELCOMES = {"dering": WELCOME_DERING, "vitali": WELCOME_VITALI, "imperator": WELCOME_IMPERATOR}


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    sticker_service = services.get("sticker_service")

    user = update.effective_user
    if user_repo:
        user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
        teacher = user_repo.get_teacher(user_id)
    else:
        teacher = "vitali"

    text = WELCOMES.get(teacher, WELCOME_VITALI)
    await update.message.reply_text(text)

    if sticker_service:
        sticker_id = sticker_service.get_sticker_for_event("greeting")
        if sticker_id:
            try:
                await update.message.reply_sticker(sticker_id)
            except Exception as e:
                logger.debug("Sticker send failed: %s", e)
