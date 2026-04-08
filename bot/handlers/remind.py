"""Stub fuer /remind — delegiert an remind_handler."""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.remind_handler import handle_remind as _real


async def handle_remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _real(update, context)
