"""Session-Manager: verwaltet den Lernzyklus pro User.

Zyklus:
  IDLE -> LESSON_ACTIVE -> PRACTICE -> QUIZ -> IDLE

Neu gegenueber alter Version:
- Timeout nach SESSION_TIMEOUT_SECONDS Inaktivitaet
- Antwortqualitaet 0-5 statt bool (SM-2-kompatibel)
- Serialisierung zu/von Dict fuer persistente Speicherung
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# Timeout: Session verfaellt nach 10 Minuten Inaktivitaet
SESSION_TIMEOUT_SECONDS = 600
SESSION_KEY = "learning_session"


class LearningPhase(str, Enum):
    IDLE = "idle"                    # kein aktiver Lernmodus
    LESSON_ACTIVE = "lesson_active"  # Vokabeln werden gerade gezeigt
    PRACTICE = "practice"            # Uebungsfragen zu den gelernten Woertern
    QUIZ = "quiz"                    # Formales Quiz (Multiple Choice)


@dataclass
class LearningSession:
    phase: LearningPhase = LearningPhase.IDLE
    lesson_words: List[Dict[str, Any]] = field(default_factory=list)
    practice_index: int = 0
    # Qualitaet 0-5 statt bool (SM-2-kompatibel)
    practice_results: Dict[int, int] = field(default_factory=dict)  # vocab_id -> quality 0-5
    quiz_score: int = 0
    quiz_total: int = 0
    last_activity: float = field(default_factory=time.time)
    active_topic: Optional[str] = None  # Topic-Filter fuer diese Session

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def is_expired(self) -> bool:
        """Gibt True zurueck wenn die Session durch Inaktivitaet abgelaufen ist."""
        return (
            self.phase != LearningPhase.IDLE
            and time.time() - self.last_activity > SESSION_TIMEOUT_SECONDS
        )

    def touch(self) -> None:
        """Aktualisiert den Inaktivitaets-Timestamp."""
        self.last_activity = time.time()

    def start_lesson(
        self,
        words: List[Dict[str, Any]],
        topic: Optional[str] = None,
    ) -> None:
        self.phase = LearningPhase.LESSON_ACTIVE
        self.lesson_words = words
        self.practice_index = 0
        self.practice_results = {}
        self.quiz_score = 0
        self.quiz_total = 0
        self.active_topic = topic
        self.touch()

    def start_practice(self) -> None:
        self.phase = LearningPhase.PRACTICE
        self.practice_index = 0
        self.touch()

    def start_quiz(self) -> None:
        self.phase = LearningPhase.QUIZ
        self.quiz_score = 0
        self.quiz_total = 0
        self.touch()

    def finish(self) -> None:
        self.phase = LearningPhase.IDLE
        self.touch()

    # ------------------------------------------------------------------
    # Practice-Logik
    # ------------------------------------------------------------------

    def current_practice_word(self) -> Optional[Dict[str, Any]]:
        if self.practice_index < len(self.lesson_words):
            return self.lesson_words[self.practice_index]
        return None

    def advance_practice(self, quality: int | bool) -> bool:
        """Geht zum naechsten Wort. Gibt True zurueck wenn alle Woerter geuebt wurden.

        Args:
            quality: SM-2-Qualitaet 0-5 ODER bool fuer Rueckwaertskompatibilitaet.
                     bool True -> 4, bool False -> 1
        """
        self.touch()
        if self.practice_index < len(self.lesson_words):
            vocab_id = self.lesson_words[self.practice_index]["vocab_id"]
            if isinstance(quality, bool):
                quality = 4 if quality else 1
            quality = max(0, min(5, int(quality)))
            self.practice_results[vocab_id] = quality
        self.practice_index += 1
        return self.practice_index >= len(self.lesson_words)

    # ------------------------------------------------------------------
    # Statistik-Hilfsmethoden
    # ------------------------------------------------------------------

    def correct_count(self) -> int:
        """Anzahl korrekter Antworten (Qualitaet >= 3)."""
        return sum(1 for q in self.practice_results.values() if q >= 3)

    def accuracy_percent(self) -> int:
        """Genauigkeit in Prozent (0-100)."""
        total = len(self.practice_results)
        if total == 0:
            return 0
        return round(self.correct_count() / total * 100)

    # ------------------------------------------------------------------
    # Serialisierung (fuer persistente Speicherung in DB)
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "lesson_words": self.lesson_words,
            "practice_index": self.practice_index,
            "practice_results": {str(k): v for k, v in self.practice_results.items()},
            "quiz_score": self.quiz_score,
            "quiz_total": self.quiz_total,
            "last_activity": self.last_activity,
            "active_topic": self.active_topic,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningSession":
        session = cls()
        session.phase = LearningPhase(data.get("phase", "idle"))
        session.lesson_words = data.get("lesson_words", [])
        session.practice_index = int(data.get("practice_index", 0))
        session.practice_results = {
            int(k): int(v)
            for k, v in data.get("practice_results", {}).items()
        }
        session.quiz_score = int(data.get("quiz_score", 0))
        session.quiz_total = int(data.get("quiz_total", 0))
        session.last_activity = float(data.get("last_activity", time.time()))
        session.active_topic = data.get("active_topic")
        return session


# ------------------------------------------------------------------
# Hilfsfunktionen fuer context.user_data
# ------------------------------------------------------------------

def get_session(user_data: dict) -> LearningSession:
    """Gibt die aktuelle Session zurueck oder erstellt eine neue.

    Prueft automatisch auf Timeout und setzt abgelaufene Sessions zurueck.
    """
    if SESSION_KEY not in user_data:
        user_data[SESSION_KEY] = LearningSession()
        return user_data[SESSION_KEY]

    session: LearningSession = user_data[SESSION_KEY]
    if session.is_expired():
        user_data[SESSION_KEY] = LearningSession()
    return user_data[SESSION_KEY]


def clear_session(user_data: dict) -> None:
    user_data.pop(SESSION_KEY, None)
