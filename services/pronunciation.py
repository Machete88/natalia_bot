"""Aussprache-Check: Nutzer spricht deutsches Wort -> Whisper transkribiert -> Bewertung."""
from __future__ import annotations

import logging
from pathlib import Path
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def _similarity(a: str, b: str) -> float:
    """Normalisierter Aehnlichkeitswert 0.0-1.0 (case-insensitive)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def evaluate_pronunciation(expected: str, recognised: str) -> dict:
    """
    Vergleicht erwartetes Wort mit dem von Whisper erkannten Text.
    Gibt dict mit score (0-100), grade und feedback zurueck.
    """
    score = round(_similarity(expected, recognised) * 100)

    if score >= 90:
        grade = "perfect"
    elif score >= 70:
        grade = "good"
    elif score >= 50:
        grade = "ok"
    else:
        grade = "try_again"

    return {
        "expected": expected,
        "recognised": recognised,
        "score": score,
        "grade": grade,
    }


FEEDBACK = {
    "vitali": {
        "perfect":   "\U0001f31f Отлично! Почти идеально! *{expected}* \U0001f44f",
        "good":      "\U0001f44d Хорошо! Почти правильно! ({score}%). Ещё раз:",
        "ok":        "\u26a0\ufe0f Неплохо — я услышал *{recognised}* ({score}%). Попробуй ещё: *{expected}*",
        "try_again": "\u274c Не совсем — я услышал *{recognised}*. Правильно: *{expected}*. Попробуй ещё раз!",
    },
    "dering": {
        "perfect":   "\u2705 Верно. *{expected}*",
        "good":      "\U0001f4ca Удовлетворительно ({score}%). Правильно: *{expected}*",
        "ok":        "\u26a0\ufe0f Распознано: *{recognised}* ({score}%). Ожидалось: *{expected}*",
        "try_again": "\u274c Неверно. Ожидалось *{expected}*, распознано *{recognised}*.",
    },
    "imperator": {
        "perfect":   "\U0001f525 *{expected}*. Идеально.",
        "good":      "\U0001f4aa Хорошо ({score}%). Ещё раз.",
        "ok":        "\u26a0\ufe0f {score}%. Повтори: *{expected}*",
        "try_again": "\u274c {score}%. Ещё раз. Слово: *{expected}*",
    },
}


def format_feedback(result: dict, teacher: str) -> str:
    tmpl = FEEDBACK.get(teacher, FEEDBACK["vitali"])[result["grade"]]
    return tmpl.format(**result)


PRONUNCIATION_TRIGGER_PHRASES = {
    "ru": ["произнеси", "повтори", "скажи", "прочитай"],
}
