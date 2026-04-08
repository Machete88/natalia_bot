"""Kompatibilitaets-Re-Export fuer /pronounce Handler."""
from bot.handlers.pronounce_handler import cmd_pronounce as handle_pronounce
from bot.handlers.pronounce_handler import handle_voice_pronounce as handle_voice_pronunciation

__all__ = ["handle_pronounce", "handle_voice_pronunciation"]
