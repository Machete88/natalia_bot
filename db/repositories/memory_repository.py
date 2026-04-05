"""Memory/conversation history repository."""
from __future__ import annotations
import sqlite3
from typing import List, Dict


class MemoryRepository:
    MAX_HISTORY = 20

    def __init__(self, db_path: str) -> None:
        self._path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_message(self, user_id: int, role: str, content: str, teacher: str = "") -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO memory (user_id, role, content, teacher) VALUES (?, ?, ?, ?)",
                (user_id, role, content, teacher),
            )
            # Trim old messages
            conn.execute(
                """DELETE FROM memory WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM memory WHERE user_id = ?
                    ORDER BY id DESC LIMIT ?
                )""",
                (user_id, user_id, self.MAX_HISTORY),
            )

    def get_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content, teacher FROM memory WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]
