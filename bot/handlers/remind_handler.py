"""Telegram-Handler fuer /remind Befehl.
Wird in app/main.py registriert.
"""
from telegram.ext import CommandHandler
from services.reminder import cmd_remind

remind_handler = CommandHandler("remind", cmd_remind)
