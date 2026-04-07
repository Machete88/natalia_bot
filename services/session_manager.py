"""Session-Manager: verwaltet den Lernzyklus pro User.

Zyklus:
  IDLE -> LESSON_ACTIVE -> PRACTICE -> QUIZ -> IDLE

Wird im context.user_data gespeichert (bleibt solange der Bot läuft).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class LearningPhase(str, Enum):
    IDLE = "idle"                    # kein aktiver Lernmodus
    LESSON_ACTIVE = "lesson_active"  # Vokabeln werden gerade gezeigt
    PRACTICE = "practice"            # Übungsfragen zu den gelernten Wörtern
    QUIZ = "quiz"                    # Formales Quiz (Multiple Choice)


SESSION_KEY = "learning_session"


@dataclass
class LearningSession:
    phase: LearningPhase = LearningPhase.IDLE
    lesson_words: List[Dict[str, Any]] = field(default_factory=list)  # [{word_de, word_ru, vocab_id}]
    practice_index: int = 0          # welches Wort wird gerade geübt
    practice_results: Dict[int, bool] = field(default_factory=dict)  # vocab_id -> correct
    quiz_score: int = 0
    quiz_total: int = 0

    def start_lesson(self, words: List[Dict[str, Any]]) -> None:
        self.phase = LearningPhase.LESSON_ACTIVE
        self.lesson_words = words
        self.practice_index = 0
        self.practice_results = {}
        self.quiz_score = 0
        self.quiz_total = 0

    def start_practice(self) -> None:
        self.phase = LearningPhase.PRACTICE
        self.practice_index = 0

    def current_practice_word(self) -> Optional[Dict[str, Any]]:
        if self.practice_index < len(self.lesson_words):
            return self.lesson_words[self.practice_index]
        return None

    def advance_practice(self, correct: bool) -> bool:
        """Geht zum nächsten Wort. Gibt True zurück wenn alle Wörter geübt wurden."""
        if self.practice_index < len(self.lesson_words):
            vocab_id = self.lesson_words[self.practice_index]["vocab_id"]
            self.practice_results[vocab_id] = correct
        self.practice_index += 1
        return self.practice_index >= len(self.lesson_words)

    def start_quiz(self) -> None:
        self.phase = LearningPhase.QUIZ
        self.quiz_score = 0
        self.quiz_total = 0

    def finish(self) -> None:
        self.phase = LearningPhase.IDLE


def get_session(user_data: dict) -> LearningSession:
    if SESSION_KEY not in user_data:
        user_data[SESSION_KEY] = LearningSession()
    return user_data[SESSION_KEY]


def clear_session(user_data: dict) -> None:
    user_data.pop(SESSION_KEY, None)
