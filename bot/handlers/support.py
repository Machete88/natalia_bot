"""Support-Modus: Natalia tippt das Codewort -> Admin wird eingebunden.

Fluss:
1. Natalia schickt das Codewort (SUPPORT_CODEWORD in .env).
2. Bot bestaetigt diskret und benachrichtigt den Admin.
3. Alle Nachrichten von Natalia werden an Admin weitergeleitet.
4. Admin antwortet -> Bot leitet es als Imperator an Natalia.
5. /endsupport (Admin ODER Natalia) beendet den Modus.
"""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

SUPPORT_MODE_KEY    = "support_mode_active"
SUPPORT_CHAT_ID_KEY = "support_chat_id"

ENTRY_MSG = "\U0001f525 На связи. Чем могу помочь?"
EXIT_MSG   = "\U0001f525 Понял. До следующего раза."


def is_support_active(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.application.bot_data.get(SUPPORT_MODE_KEY, False))


async def activate_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data.get("settings")
    user = update.effective_user
    natalia_chat_id = update.effective_chat.id

    context.application.bot_data[SUPPORT_MODE_KEY]    = True
    context.application.bot_data[SUPPORT_CHAT_ID_KEY] = natalia_chat_id

    await update.message.reply_text(ENTRY_MSG)

    if settings:
        admin_id = settings.admin_user_id
        name = user.first_name or "Natalia"
        await context.bot.send_message(
            chat_id=admin_id,
            text=(
                f"\U0001f514 *Support-Modus aktiv*\n"
                f"{name} braucht Hilfe.\n"
                f"Alle Nachrichten werden hierher weitergeleitet.\n\n"
                f"Выключить: /endsupport"
            ),
            parse_mode="Markdown",
        )
        try:
            from services.email_alert import send_support_alert
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, send_support_alert, name)
        except Exception as e:
            logger.warning("E-Mail-Alert fehlgeschlagen: %s", e)

        logger.info("Support mode activated by %s", user.id)


async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data.get("settings")
    if not settings:
        return
    admin_id = settings.admin_user_id
    user = update.effective_user
    name = user.first_name or "Natalia"

    if update.message.text:
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"\U0001f464 *{name}*: {update.message.text}",
            parse_mode="Markdown",
        )
    elif update.message.voice:
        await context.bot.send_message(chat_id=admin_id, text=f"\U0001f3a4 *{name}* schickt eine Sprachnachricht:", parse_mode="Markdown")
        await context.bot.forward_message(chat_id=admin_id, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
    elif update.message.photo:
        await context.bot.send_message(chat_id=admin_id, text=f"\U0001f4f7 *{name}* schickt ein Bild:", parse_mode="Markdown")
        await context.bot.forward_message(chat_id=admin_id, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
    elif update.message.document:
        await context.bot.send_message(chat_id=admin_id, text=f"\U0001f4ce *{name}* schickt ein Dokument:", parse_mode="Markdown")
        await context.bot.forward_message(chat_id=admin_id, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_support_active(context):
        return
    natalia_chat_id = context.application.bot_data.get(SUPPORT_CHAT_ID_KEY)
    if not natalia_chat_id:
        return
    text = update.message.text or ""
    if text.strip().lower() == "/endsupport":
        await deactivate_support(update, context)
        return
    if text:
        await context.bot.send_message(
            chat_id=natalia_chat_id,
            text=f"\U0001f525 *Imperator*: {text}",
            parse_mode="Markdown",
        )


async def deactivate_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings  = context.bot_data.get("settings")
    natalia_chat_id = context.application.bot_data.get(SUPPORT_CHAT_ID_KEY)
    context.application.bot_data[SUPPORT_MODE_KEY]    = False
    context.application.bot_data[SUPPORT_CHAT_ID_KEY] = None
    if natalia_chat_id:
        try:
            await context.bot.send_message(chat_id=natalia_chat_id, text=EXIT_MSG)
        except Exception as e:
            logger.warning("Exit msg failed: %s", e)
    if settings:
        try:
            await context.bot.send_message(
                chat_id=settings.admin_user_id,
                text="\u2705 Support-Modus beendet. Bot läuft wieder normal."
            )
        except Exception as e:
            logger.warning("Admin confirm failed: %s", e)
    logger.info("Support mode deactivated.")
