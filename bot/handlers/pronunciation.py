"""Handler fuer /pronounce — leitet an pronounce_handler weiter (Kompatibilitaets-Alias)."""
from bot.handlers.pronounce_handler import handle_pronounce

__all__ = ["handle_pronounce"]
