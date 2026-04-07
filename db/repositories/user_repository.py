"""User repository."""
from __future__ import annotations
import sqlite3
from typing import Optional


class UserRepository:
    def __init__(self, db_path: str) -> None:
        self._path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_or_create_user(self, telegram_id: int, name: str = "") -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE users SET last_seen = datetime('now') WHERE telegram_id = ?",
                    (telegram_id,),
                )
                return row["id"]
            cur = conn.execute(
                "INSERT INTO users (telegram_id, name) VALUES (?, ?)",
                (telegram_id, name),
            )
            return cur.lastrowid

    def get_teacher(self, user_id: int) -> str:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT teacher FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return row["teacher"] if row else "vitali"

    def set_teacher(self, user_id: int, teacher: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET teacher = ? WHERE id = ?", (teacher, user_id)
            )

    def get_level(self, user_id: int) -> str:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT level FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return row["level"] if row else "beginner"

    def set_level(self, user_id: int, level: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET level = ? WHERE id = ?", (level, user_id)
            )

    def set_preference(self, user_id: int, key: str, value: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_preferences (user_id, key, value) VALUES (?, ?, ?)",
                (user_id, key, value),
            )

    def get_preference(self, user_id: int, key: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM user_preferences WHERE user_id = ? AND key = ?",
                (user_id, key),
            ).fetchone()
            return row["value"] if row else None
