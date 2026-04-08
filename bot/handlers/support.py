"""Support-Modus — leitet Nachrichten an Admin weiter."""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

_SUPPORT_KEY = "_support_active"


def is_support_active(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.bot_data.get(_SUPPORT_KEY))


async def activate_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot_data[_SUPPORT_KEY] = True
    await update.message.reply_text("ℹ️ Support-Modus aktiv. Nachrichten gehen an Admin.")


async def deactivate_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot_data[_SUPPORT_KEY] = False
    await update.message.reply_text("✅ Support-Modus deaktiviert.")


async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data.get("settings")
    if not settings:
        return
    text = update.message.text or ""
    try:
        await context.bot.send_message(
            chat_id=settings.admin_user_id,
            text=f"[Support] {update.effective_user.first_name}: {text}",
        )
    except Exception as e:
        logger.warning("Forward to admin failed: %s", e)


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.bot_data.get("settings")
    if not settings:
        return
    text = update.message.text or ""
    try:
        await context.bot.send_message(
            chat_id=settings.authorized_user_id,
            text=f"[Admin]: {text}",
        )
    except Exception as e:
        logger.warning("Admin reply failed: %s", e)
