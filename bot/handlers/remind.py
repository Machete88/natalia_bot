"""Stub fuer /remind — delegiert an reminder.cmd_remind."""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from services.reminder import cmd_remind as _real


async def handle_remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _real(update, context)
