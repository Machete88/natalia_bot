"""Handler fuer /remind — leitet an remind_handler weiter (Kompatibilitaets-Alias)."""
from bot.handlers.remind_handler import handle_remind

__all__ = ["handle_remind"]
