"""Stub fuer /pronounce — delegiert an pronounce_handler."""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.pronounce_handler import cmd_pronounce as _real


async def handle_pronounce(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _real(update, context)
