"""Lesson Planner: waehlt passende Vokabeln fuer jede Session.

Strategie:
- Faellige Wiederholungen (next_review_date <= heute) zuerst, max. MAX_REVIEWS
- Dann neue Woerter fuer Level/Topic bis MAX_STEPS erreicht

SM-2-Algorithmus wird fuer update_progress genutzt.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from services.sm2_engine import SM2Result, bool_to_quality, sm2_update


@dataclass
class LessonStep:
    """Ein einzelner Schritt in einer Lerneinheit."""
    type: str          # 'new_vocab' | 'review_vocab'
    vocab_id: int
    word_de: str
    word_ru: str
    example_de: str
    example_ru: str
    topic: str = ""


class LessonPlanner:
    """Vokabel-Planung per User mit SM-2-Algorithmus."""

    MAX_STEPS = 5
    MAX_REVIEWS = 3

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    # ------------------------------------------------------------------
    # Hilfsmethoden
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Oeffentliche API
    # ------------------------------------------------------------------

    def next_steps(
        self,
        user_id: int,
        topic: Optional[str] = None,
        today: Optional[date] = None,
    ) -> List[LessonStep]:
        """Gibt die naechsten Lernschritte zurueck.

        Args:
            user_id: Interne User-ID (aus DB)
            topic:   Optionaler Topic-Filter (z.B. 'Essen', 'Reisen')
            today:   Datum fuer Faelligkeits-Check (Standard: heute)
        """
        today_str = (today or date.today()).isoformat()
        level = self._get_level(user_id)
        steps: List[LessonStep] = []

        with self._conn() as conn:
            # 1) Faellige Wiederholungen (SM-2: next_review_date <= heute)
            reviews = conn.execute(
                """
                SELECT v.id, v.word_de, v.word_ru,
                       v.example_de, v.example_ru, v.topic
                FROM vocab_progress vp
                JOIN vocab_items v ON vp.vocab_id = v.id
                WHERE vp.user_id = ?
                  AND vp.status IN ('learning', 'new')
                  AND (
                      vp.next_review_date IS NULL
                      OR vp.next_review_date <= ?
                  )
                ORDER BY vp.next_review_date ASC NULLS FIRST
                LIMIT ?
                """,
                (user_id, today_str, self.MAX_REVIEWS),
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
                        topic=row["topic"] or "",
                    )
                )

            remaining = self.MAX_STEPS - len(steps)
            if remaining <= 0:
                return steps

            # 2) Neue Woerter (noch kein Progress-Eintrag)
            params: List[object] = [level]
            topic_clause = ""
            if topic:
                topic_clause = "AND v.topic = ?"
                params.append(topic)

            params.extend([user_id, remaining])

            new_items = conn.execute(
                f"""
                SELECT v.id, v.word_de, v.word_ru,
                       v.example_de, v.example_ru, v.topic
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
                        topic=row["topic"] or "",
                    )
                )

        return steps

    def available_topics(self, user_id: int) -> List[str]:
        """Gibt alle verfuegbaren Topics fuer das Level des Users zurueck."""
        level = self._get_level(user_id)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT topic FROM vocab_items WHERE level = ? ORDER BY topic",
                (level,),
            ).fetchall()
        return [r["topic"] for r in rows if r["topic"]]

    def due_count(self, user_id: int, today: Optional[date] = None) -> int:
        """Gibt die Anzahl faelliger Wiederholungen zurueck."""
        today_str = (today or date.today()).isoformat()
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM vocab_progress
                WHERE user_id = ?
                  AND status IN ('learning', 'new')
                  AND (next_review_date IS NULL OR next_review_date <= ?)
                """,
                (user_id, today_str),
            ).fetchone()
        return int(row["cnt"]) if row else 0

    def update_progress(
        self,
        user_id: int,
        results: Dict[int, int],  # vocab_id -> Qualitaet 0-5
        today: Optional[date] = None,
    ) -> None:
        """Aktualisiert Lernfortschritt nach SM-2.

        Args:
            results: Mapping vocab_id -> Qualitaet (0-5).
                     Fuer Rueckwaerts-Compat auch bool akzeptiert.
            today:   Datum fuer next_review_date (Standard: heute)
        """
        if not results:
            return

        today_obj = today or date.today()

        with self._conn() as conn:
            for vocab_id, quality_or_bool in results.items():
                # Rueckwaertskompatibilitaet: bool -> int
                if isinstance(quality_or_bool, bool):
                    quality = bool_to_quality(quality_or_bool)
                else:
                    quality = int(quality_or_bool)
                    quality = max(0, min(5, quality))

                row = conn.execute(
                    """
                    SELECT id, status, ease_factor, interval_days, repetitions
                    FROM vocab_progress
                    WHERE user_id = ? AND vocab_id = ?
                    """,
                    (user_id, vocab_id),
                ).fetchone()

                if row:
                    result: SM2Result = sm2_update(
                        quality=quality,
                        ease_factor=float(row["ease_factor"] or 2.5),
                        interval_days=int(row["interval_days"] or 0),
                        repetitions=int(row["repetitions"] or 0),
                        today=today_obj,
                    )
                    conn.execute(
                        """
                        UPDATE vocab_progress
                        SET status            = ?,
                            ease_factor       = ?,
                            interval_days     = ?,
                            repetitions       = ?,
                            next_review_date  = ?,
                            last_seen         = datetime('now')
                        WHERE id = ?
                        """,
                        (
                            result.status,
                            result.ease_factor,
                            result.interval_days,
                            result.repetitions,
                            result.next_review_date,
                            row["id"],
                        ),
                    )
                else:
                    # Neuer Eintrag: erstes SM-2-Update
                    result = sm2_update(
                        quality=quality,
                        today=today_obj,
                    )
                    conn.execute(
                        """
                        INSERT INTO vocab_progress
                            (user_id, vocab_id, status, ease_factor,
                             interval_days, repetitions, next_review_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            vocab_id,
                            result.status,
                            result.ease_factor,
                            result.interval_days,
                            result.repetitions,
                            result.next_review_date,
                        ),
                    )
