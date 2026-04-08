"""Stub fuer /remind — delegiert an services.reminder.cmd_remind."""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from services.reminder import cmd_remind as handle_remind

__all__ = ["handle_remind"]
