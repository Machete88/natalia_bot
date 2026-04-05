"""Memory/conversation history repository - pro Lehrer getrennt."""
from __future__ import annotations
import sqlite3
from typing import List, Dict, Optional


class MemoryRepository:
    MAX_HISTORY = 30  # Gesamt pro User gespeichert
    DEFAULT_CONTEXT = 12  # Standard-Kontext für LLM

    def __init__(self, db_path: str) -> None:
        self._path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_message(
        self, user_id: int, role: str, content: str, teacher: str = ""
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO memory (user_id, role, content, teacher) VALUES (?, ?, ?, ?)",
                (user_id, role, content, teacher),
            )
            # Trim: pro User+Teacher nur MAX_HISTORY behalten
            conn.execute(
                """
                DELETE FROM memory
                WHERE user_id = ? AND (teacher = ? OR teacher = '')
                AND id NOT IN (
                    SELECT id FROM memory
                    WHERE user_id = ? AND (teacher = ? OR teacher = '')
                    ORDER BY id DESC LIMIT ?
                )
                """,
                (user_id, teacher, user_id, teacher, self.MAX_HISTORY),
            )

    def get_history(
        self,
        user_id: int,
        limit: int = DEFAULT_CONTEXT,
        teacher: Optional[str] = None,
    ) -> List[Dict]:
        """Gibt die letzten `limit` Nachrichten zurück.
        Wenn teacher angegeben: nur Nachrichten mit diesem Lehrer.
        Sonst: alle Nachrichten des Users.
        """
        with self._conn() as conn:
            if teacher:
                rows = conn.execute(
                    """
                    SELECT role, content, teacher FROM memory
                    WHERE user_id = ? AND (teacher = ? OR teacher = '')
                    ORDER BY id DESC LIMIT ?
                    """,
                    (user_id, teacher, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT role, content, teacher FROM memory
                    WHERE user_id = ?
                    ORDER BY id DESC LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()
            return [dict(r) for r in reversed(rows)]

    def clear_history(self, user_id: int, teacher: Optional[str] = None) -> None:
        """Löscht den Verlauf (optional nur für einen Lehrer)."""
        with self._conn() as conn:
            if teacher:
                conn.execute(
                    "DELETE FROM memory WHERE user_id = ? AND teacher = ?",
                    (user_id, teacher),
                )
            else:
                conn.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))

    def get_stats(self, user_id: int) -> Dict[str, int]:
        """Gibt Nachrichtenanzahl pro Lehrer zurück."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT teacher, COUNT(*) as cnt FROM memory
                WHERE user_id = ? GROUP BY teacher
                """,
                (user_id,),
            ).fetchall()
            return {r["teacher"] or "unknown": r["cnt"] for r in rows}
