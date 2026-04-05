"""Handler for /start command."""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

WELCOME = {
    "dering": (
        "Добрый день. Я Деринг — ваш преподаватель немецкого языка. "
        "Мы начнём с основ. Напишите «Привет» или выберите команду."
    ),
    "vitali": (
        "Привет, Наташа! \U0001f60a Я Витали — твой учитель немецкого. "
        "Рад тебя видеть! Чем хочешь заняться сегодня?"
    ),
    "imperator": (
        "Ты здесь. Хорошо. Я Император. "
        "Немецкий язык — это не просто слова. Это другой способ видеть мир. Готова?"
    ),
}

COMMAND_MENU = """
Вот что я умею:
\U0001f4da /lesson \u2014 5 новых слов учить
\U0001f914 /quiz \u2014 викторина — угадай слово
\U0001f4ca /progress \u2014 твой прогресс
\U0001f4d0 /setlevel a1 \u2014 установить уровень
\U0001f468\u200d\U0001f3eb /teacher vitali \u2014 сменить учителя
\U0001f4f8 Фото \u2014 проверка домашней работы
\U0001f3a4 Голос \u2014 говори со мной по-немецки
"""


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

    welcome = WELCOME.get(teacher, WELCOME["vitali"])
    await update.message.reply_text(f"{welcome}{COMMAND_MENU}")

    if sticker_service:
        sticker_id = sticker_service.get_sticker_for_event("greeting")
        if sticker_id:
            try:
                await update.message.reply_sticker(sticker_id)
            except Exception as e:
                logger.debug("Sticker send failed: %s", e)
