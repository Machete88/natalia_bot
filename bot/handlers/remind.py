"""Kompatibilitaets-Re-Export fuer /remind Handler."""
from services.reminder import cmd_remind as handle_remind

__all__ = ["handle_remind"]
