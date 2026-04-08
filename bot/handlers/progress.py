"""Stub fuer /progress — delegiert an progress_handler."""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.progress_handler import handle_progress as _real


async def handle_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _real(update, context)
