"""Lesson planner: waehlt passende Vokabeln fuer jede Session."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class LessonStep:
    """Ein einzelner Schritt in einer Lerneinheit."""

    type: str  # "new_vocab" | "review_vocab"
    vocab_id: int
    word_de: str
    word_ru: str
    example_de: str
    example_ru: str


class LessonPlanner:
    """Einfache Vokabel-Planung pro Nutzer.

    Strategie pro Session:
    - Maximal 5 Items
      - Bis zu 2 Wiederholungen (status = "learning")
      - Der Rest neue Woerter (status = "new") für das aktuelle Level.
    """

    MAX_STEPS = 5
    MAX_REVIEWS = 2

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_level(self, user_id: int) -> str:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT language_level FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return row["language_level"] if row and row["language_level"] else "beginner"

    def next_steps(self, user_id: int, topic: Optional[str] = None) -> List[LessonStep]:
        """Plane die naechsten Lernschritte fuer einen Nutzer."""

        level = self._get_level(user_id)
        steps: List[LessonStep] = []

        with self._conn() as conn:
            # 1) Wiederholungen: Items mit status "learning", sortiert nach last_seen
            reviews = conn.execute(
                """
                SELECT v.id, v.word_de, v.word_ru, v.example_de, v.example_ru
                FROM vocab_progress vp
                JOIN vocab_items v ON vp.vocab_id = v.id
                WHERE vp.user_id = ? AND vp.status = 'learning'
                ORDER BY vp.last_seen ASC
                LIMIT ?
                """,
                (user_id, self.MAX_REVIEWS),
            ).fetchall()

            for row in reviews:
                steps.append(
                    LessonStep(
                        type="review_vocab",
                        vocab_id=row["id"],
                        word_de=row["word_de"],
                        word_ru=row["word_ru"],
                        example_de=row["example_de"] or "",
                        example_ru=row["example_ru"] or "",
                    )
                )

            remaining = self.MAX_STEPS - len(steps)
            if remaining <= 0:
                return steps

            # 2) Neue Woerter fuer Level/Topic, die noch nicht im Progress sind
            params: List[object] = [level]
            topic_clause = ""
            if topic:
                topic_clause = "AND v.topic = ?"
                params.append(topic)

            params.extend([user_id, remaining])

            new_items = conn.execute(
                f"""
                SELECT v.id, v.word_de, v.word_ru, v.example_de, v.example_ru
                FROM vocab_items v
                WHERE v.level = ? {topic_clause}
                  AND v.id NOT IN (
                      SELECT vocab_id FROM vocab_progress WHERE user_id = ?
                  )
                ORDER BY v.id ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()

            for row in new_items:
                steps.append(
                    LessonStep(
                        type="new_vocab",
                        vocab_id=row["id"],
                        word_de=row["word_de"],
                        word_ru=row["word_ru"],
                        example_de=row["example_de"] or "",
                        example_ru=row["example_ru"] or "",
                    )
                )

        return steps

    def update_progress(self, user_id: int, results: Dict[int, bool]) -> None:
        """Aktualisiere Lernfortschritt nach einer Session.

        results: Mapping vocab_id -> True/False, ob richtig verwendet/verstanden.
        """

        if not results:
            return

        with self._conn() as conn:
            for vocab_id, correct in results.items():
                row = conn.execute(
                    """
                    SELECT id, status, correct_streak
                    FROM vocab_progress
                    WHERE user_id = ? AND vocab_id = ?
                    """,
                    (user_id, vocab_id),
                ).fetchone()

                if row:
                    streak = int(row["correct_streak"]) + 1 if correct else 0
                    status = row["status"]

                    if correct and streak >= 3:
                        status = "mastered"
                    elif correct:
                        status = "learning"
                    else:
                        status = "learning"

                    conn.execute(
                        """
                        UPDATE vocab_progress
                        SET status = ?, correct_streak = ?, last_seen = datetime('now')
                        WHERE id = ?
                        """,
                        (status, streak, row["id"]),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO vocab_progress (user_id, vocab_id, status, correct_streak)
                        VALUES (?, ?, ?, ?)
                        """,
                        (user_id, vocab_id, "learning" if correct else "new", 1 if correct else 0),
                    )
