"""Streak-Tracking: zaehlt Tage mit Lernaktivitaet in Folge."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Tuple


class StreakService:
    def __init__(self, db_path: str) -> None:
        self._db = db_path

    def record_activity(self, user_id: int) -> Tuple[int, int, bool]:
        """Registriert eine Lernaktivitaet fuer heute.

        Gibt (current_streak, longest_streak, is_new_day) zurueck.
        """
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        with sqlite3.connect(self._db) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM streaks WHERE user_id = ?", (user_id,)
            ).fetchone()

            if not row:
                conn.execute(
                    "INSERT INTO streaks (user_id, last_activity_date, current_streak, longest_streak) VALUES (?,?,1,1)",
                    (user_id, today),
                )
                return 1, 1, True

            last = row["last_activity_date"]

            if last == today:
                # Bereits heute aktiv
                return row["current_streak"], row["longest_streak"], False

            if last == yesterday:
                # Streak fortsetzen
                new_streak = row["current_streak"] + 1
                new_longest = max(new_streak, row["longest_streak"])
            else:
                # Streak gebrochen
                new_streak = 1
                new_longest = row["longest_streak"]

            conn.execute(
                "UPDATE streaks SET last_activity_date=?, current_streak=?, longest_streak=? WHERE user_id=?",
                (today, new_streak, new_longest, user_id),
            )
            return new_streak, new_longest, True

    def get_streak(self, user_id: int) -> Tuple[int, int]:
        """Gibt (current_streak, longest_streak) zurueck."""
        with sqlite3.connect(self._db) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT current_streak, longest_streak FROM streaks WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                return 0, 0
            return row["current_streak"], row["longest_streak"]
