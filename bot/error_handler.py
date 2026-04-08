"""Globaler Fehler-Handler fuer den Telegram-Bot.

Faengt alle ungefangenen Exceptions, loggt sie vollstaendig
und benachrichtigt den Admin per Telegram-Nachricht.
"""
from __future__ import annotations

import html
import logging
import traceback

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

_MAX_MSG_LEN = 3500  # Telegram-Limit: 4096, sicher bleiben


async def handle_error(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Globaler Error-Handler — wird von PTB bei jeder Exception aufgerufen."""
    settings = context.bot_data.get("settings")
    admin_id = getattr(settings, "admin_user_id", None) if settings else None

    tb_str = "".join(traceback.format_exception(
        type(context.error), context.error, context.error.__traceback__
    ))
    logger.error("Ungefangene Exception:\n%s", tb_str)

    if not admin_id:
        return

    # Update-Kontext kurz zusammenfassen
    update_info = ""
    if isinstance(update, Update):
        if update.effective_message:
            txt = (update.effective_message.text or "")[:80]
            update_info = f"Message: {html.escape(txt)}"
        elif update.callback_query:
            update_info = f"Callback: {html.escape(update.callback_query.data or '')}"

    snippet = tb_str[-_MAX_MSG_LEN:] if len(tb_str) > _MAX_MSG_LEN else tb_str
    msg = (
        f"\U0001f6a8 <b>Bot-Fehler</b>\n"
        f"{html.escape(update_info)}\n"
        f"<pre>{html.escape(snippet)}</pre>"
    )

    try:
        await context.bot.send_message(
            chat_id=admin_id,
            text=msg,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Admin-Benachrichtigung fehlgeschlagen: %s", e)
