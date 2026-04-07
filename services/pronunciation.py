"""Aussprache-Feedback: Nutzer spricht ein deutsches Wort,
Whisper transkribiert -> Bot vergleicht mit Zielwort -> bewertet.
"""
from __future__ import annotations
import logging
import difflib

logger = logging.getLogger(__name__)

PRONOUNCE_KEY = "pronounce_target"

# Einheitliche Noten-Grenzen
_GRADES = [
    (90, "perfect"),
    (70, "good"),
    (50, "ok"),
    (0,  "try_again"),
]


def _normalize(text: str) -> str:
    text = text.lower().strip()
    for old, new in {"\u00e4": "ae", "\u00f6": "oe", "\u00fc": "ue", "\u00df": "ss"}.items():
        text = text.replace(old, new)
    return "".join(c for c in text if c.isalpha() or c == " ")


def evaluate_pronunciation(target: str, spoken: str) -> dict:
    """Bewertet Aussprache.
    Gibt {'score': 0-100, 'grade': str, 'feedback': str, 'word': str} zurueck.
    grade-Werte: 'perfect' | 'good' | 'ok' | 'try_again'
    """
    t = _normalize(target)
    s = _normalize(spoken)

    if not s:
        return {"score": 0, "grade": "try_again",
                "feedback": "Nichts erkannt. Nochmal.", "word": target}

    ratio = difflib.SequenceMatcher(None, t, s).ratio()
    score = 100 if t == s else int(ratio * 100)

    grade = "try_again"
    for threshold, g in _GRADES:
        if score >= threshold:
            grade = g
            break

    feedback_map = {
        "perfect":   "Perfekt! \U0001f3af",
        "good":      "Gut. \U0001f44d",
        "ok":        "Ueben. \U0001f4aa",
        "try_again": "Nochmal. \U0001f501",
    }
    feedback = feedback_map[grade]

    if t != s and score < 90:
        diff_hints = [
            f"'{sw}' \u2192 '{tw}'"
            for tw, sw in zip(t.split(), s.split()) if tw != sw
        ]
        if diff_hints:
            feedback += f"\n\U0001f4ac {', '.join(diff_hints[:2])}"

    return {"score": score, "grade": grade, "feedback": feedback, "word": target}


# Rueckwaertskompatibilitaet
score_pronunciation = evaluate_pronunciation


def format_feedback(result: dict, teacher: str = "imperator") -> str:
    """Formatiert Ergebnis-Nachricht fuer Telegram.
    Enthaelt immer das Zielwort (word) im Output.
    """
    score = result["score"]
    grade = result.get("grade", "")
    feedback = result.get("feedback", "")
    word = result.get("word", "")

    bars = int(score / 10)
    bar = "\U0001f7e9" * bars + "\u2b1c" * (10 - bars)

    base = (
        f"\U0001f3a4 *Aussprache-Ergebnis*\n\n"
        f"{bar} {score}/100\n"
        f"Bewertung: *{grade.upper()}*\n\n"
        f"*{word}*: {feedback}"
    )

    if score < 60:
        base += "\n\n\U0001f525 Inakzeptabel. Nochmal."

    return base


def build_pronounce_prompt(word_de: str, teacher: str = "imperator") -> str:
    return f"\U0001f525 AUSSPRACHE-TRAINING:\n*{word_de}*\n\nJetzt sprechen!"


def build_result_message(word_de: str, result: dict, teacher: str = "imperator") -> str:
    return format_feedback(result, teacher)
