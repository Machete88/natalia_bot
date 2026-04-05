"""Support-Modus: Natalia tippt das Codewort -> Admin (du) wird in den Chat eingebunden.

Fluss:
1. Natalia schickt das Codewort (in .env konfigurierbar).
2. Bot bestaetigt Natalia diskret und benachrichtigt den Admin.
3. Alle Nachrichten von Natalia werden nun als Forward an den Admin weitergeleitet.
4. Der Admin kann antworten -> Bot leitet es als 'Lehrer' an Natalia weiter.
5. /endsupport (vom Admin ODER Natalia) beendet den Modus.
"""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Schluessel fuer application.bot_data
SUPPORT_MODE_KEY = "support_mode_active"      # bool
SUPPORT_CHAT_ID_KEY = "support_chat_id"        # Chat-ID von Natalia

# Lehrer-Eintrittstext (je nach aktuellem Lehrer)
ENTRY_MSG = {
    "vitali":    "\U0001f91d Привет! Не переживай \u2014 я здесь \U0001f60a",
    "dering":    "\U0001f91d Добрый день. Чем могу помочь?",
    "imperator": "\U0001f525 На связи.",
}
EXIT_MSG = {
    "vitali":    "\U0001f44b До свидания! Продолжай учиться \U0001f4aa",
    "dering":    "\U0001f44b До следующего раза.",
    "imperator": "\U0001f525 На сегодня достаточно.",
}


def is_support_active(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return context.application.bot_data.get(SUPPORT_MODE_KEY, False)


async def activate_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Wird aufgerufen wenn Natalia das Codewort tippt."""
    services = context.bot_data.get("services", {})
    settings = context.bot_data.get("settings")
    user_repo = services.get("user_repo")

    user = update.effective_user
    natalia_chat_id = update.effective_chat.id

    # Support-Modus in bot_data aktivieren
    context.application.bot_data[SUPPORT_MODE_KEY] = True
    context.application.bot_data[SUPPORT_CHAT_ID_KEY] = natalia_chat_id

    teacher = "vitali"
    if user_repo:
        uid = user_repo.get_or_create_user(user.id, user.first_name or "")
        teacher = user_repo.get_teacher(uid)

    # Natalia diskret bestaetigen
    confirm = ENTRY_MSG.get(teacher, ENTRY_MSG["vitali"])
    await update.message.reply_text(confirm)

    # Admin benachrichtigen
    if settings:
        admin_id = settings.admin_user_id
        name = user.first_name or "Natalia"
        await context.bot.send_message(
            chat_id=admin_id,
            text=(
                f"\U0001f514 *Support-Modus aktiv*\n"
                f"{name} braucht Hilfe.\n"
                f"Alle Nachrichten werden hierher weitergeleitet.\n\n"
                f"Возобнови: /endsupport"
            ),
            parse_mode="Markdown",
        )
        logger.info("Support mode activated by user %s, notified admin %s", user.id, admin_id)


async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Leitet Natalias Nachricht an den Admin weiter."""
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
        caption = f"\U0001f3a4 *{name}* schickt eine Sprachnachricht:"
        await context.bot.send_message(chat_id=admin_id, text=caption, parse_mode="Markdown")
        await context.bot.forward_message(
            chat_id=admin_id,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
        )
    elif update.message.photo:
        caption = f"\U0001f4f7 *{name}* schickt ein Bild:"
        await context.bot.send_message(chat_id=admin_id, text=caption, parse_mode="Markdown")
        await context.bot.forward_message(
            chat_id=admin_id,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
        )
    elif update.message.document:
        caption = f"\U0001f4ce *{name}* schickt ein Dokument:"
        await context.bot.send_message(chat_id=admin_id, text=caption, parse_mode="Markdown")
        await context.bot.forward_message(
            chat_id=admin_id,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
        )


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin schreibt eine Nachricht -> wird als Lehrer-Antwort an Natalia weitergeleitet."""
    if not is_support_active(context):
        return

    natalia_chat_id = context.application.bot_data.get(SUPPORT_CHAT_ID_KEY)
    if not natalia_chat_id:
        return

    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    settings = context.bot_data.get("settings")

    # Teacher-Name fuer Natalia ermitteln
    teacher = "vitali"
    if user_repo and settings:
        uid = settings.authorized_user_id
        try:
            teacher = user_repo.get_teacher(uid)
        except Exception:
            pass

    teacher_labels = {
        "vitali":    "\U0001f1e9\U0001f1ea Vitali",
        "dering":    "\U0001f1e9\U0001f1ea Dering",
        "imperator": "\U0001f525 Imperator",
    }
    label = teacher_labels.get(teacher, "Lehrer")

    text = update.message.text or ""

    if text.strip().lower() == "/endsupport":
        await deactivate_support(update, context)
        return

    if text:
        await context.bot.send_message(
            chat_id=natalia_chat_id,
            text=f"*{label}*: {text}",
            parse_mode="Markdown",
        )
        logger.info("Admin reply forwarded to Natalia chat %s", natalia_chat_id)


async def deactivate_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Beendet den Support-Modus. Kann von Admin ODER Natalia ausgeloest werden."""
    services = context.bot_data.get("services", {})
    settings = context.bot_data.get("settings")
    user_repo = services.get("user_repo")

    natalia_chat_id = context.application.bot_data.get(SUPPORT_CHAT_ID_KEY)
    context.application.bot_data[SUPPORT_MODE_KEY] = False
    context.application.bot_data[SUPPORT_CHAT_ID_KEY] = None

    # Natalia benachrichtigen
    if natalia_chat_id:
        teacher = "vitali"
        if user_repo and settings:
            try:
                teacher = user_repo.get_teacher(settings.authorized_user_id)
            except Exception:
                pass
        bye = EXIT_MSG.get(teacher, EXIT_MSG["vitali"])
        try:
            await context.bot.send_message(chat_id=natalia_chat_id, text=bye)
        except Exception as e:
            logger.warning("Could not send exit msg to Natalia: %s", e)

    # Admin bestaetigen
    if settings:
        admin_id = settings.admin_user_id
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text="\u2705 Support-Modus beendet. Bot laeuft wieder normal.",
            )
        except Exception as e:
            logger.warning("Could not confirm to admin: %s", e)

    logger.info("Support mode deactivated.")
