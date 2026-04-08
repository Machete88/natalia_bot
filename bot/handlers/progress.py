"""Handler fuer /progress — leitet an progress_handler weiter (Kompatibilitaets-Alias)."""
from bot.handlers.progress_handler import handle_progress

__all__ = ["handle_progress"]
