"""Teacher handler — nur Herr Imperator. Kein Wechsel."""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes


async def handle_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Zeigt an dass es nur einen Lehrer gibt."""
    await update.message.reply_text(
        "\U0001f525 *Господин Император* — единственный учитель.\n\n"
        "_Других нет. И не будет._",
        parse_mode="Markdown"
    )


async def handle_teacher_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, teacher: str
) -> None:
    """Ignoriert alle Lehrer-Callbacks — nur Imperator."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "\U0001f525 Господин Император не допускает замены.",
        parse_mode="Markdown"
    )
