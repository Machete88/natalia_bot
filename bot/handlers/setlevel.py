"""Handler fuer /setlevel — Herr Imperator nimmt den Bericht entgegen."""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

VALID_LEVELS = ["beginner", "a1", "a2", "b1", "b2", "c1"]

LEVEL_RESPONSES = {
    "beginner": (
        "\U0001f525 *Новичок.* Господин Император начинает с самого начала.\n\n"
        "Не переживай — я буду терпелив. _Пока что._\n\n"
        "Начнём: /lesson"
    ),
    "a1": (
        "\U0001f525 *A1.* Значит, почти ничего.\n\n"
        "Господин Император видал и хуже. Работаем.\n\n"
        "Первый урок: /lesson"
    ),
    "a2": (
        "\U0001f525 *A2.* Кое-что уже знаешь — это видно.\n\n"
        "Господин Император проверит тебя лично. Будь готова.\n\n"
        "/lesson — приступай."
    ),
    "b1": (
        "\U0001f525 *B1.* Мммх. Уже интереснее.\n\n"
        "Господин Император любит, когда есть с чем работать.\n\n"
        "Докажи: /lesson"
    ),
    "b2": (
        "\U0001f525 *B2.* Ты уже кое-что умеешь, Рекрут.\n\n"
        "Но Господин Император поднимет планку. Готова?\n\n"
        "/lesson"
    ),
    "c1": (
        "\U0001f525 *C1.* Серьёзно? Тогда скучать не придётся.\n\n"
        "Господин Император будет беспощаден. _Наслаждайся._\n\n"
        "/lesson"
    ),
}

USAGE_MSG = (
    "\U0001f525 Господин Император ждёт рапорта.\n\n"
    "Укажи уровень:\n"
    "/setlevel a1\n/setlevel a2\n/setlevel b1\n/setlevel b2\n/setlevel c1"
)


async def handle_setlevel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services  = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")

    if not context.args:
        await update.message.reply_text(USAGE_MSG, parse_mode="Markdown")
        return

    level = context.args[0].strip().lower()
    if level not in VALID_LEVELS:
        await update.message.reply_text(
            f"\u274c Не знаю такого уровня: *{level}*\n\n"
            f"Допустимые: {', '.join(VALID_LEVELS)}",
            parse_mode="Markdown"
        )
        return

    if user_repo:
        user    = update.effective_user
        user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
        user_repo.set_level(user_id, level)
        user_repo.set_teacher(user_id, "imperator")

    response = LEVEL_RESPONSES.get(level, LEVEL_RESPONSES["a1"])
    await update.message.reply_text(response, parse_mode="Markdown")
