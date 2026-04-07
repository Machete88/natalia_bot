"""Aussprache-Feedback: Nutzer spricht ein deutsches Wort,
Whisper transkribiert -> Bot vergleicht mit Zielwort -> bewertet.
"""
from __future__ import annotations
import logging
import difflib

logger = logging.getLogger(__name__)

PRONOUNCE_KEY = "pronounce_target"


def _normalize(text: str) -> str:
    text = text.lower().strip()
    replacements = {
        "\u00e4": "ae", "\u00f6": "oe", "\u00fc": "ue", "\u00df": "ss",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return "".join(c for c in text if c.isalpha() or c == " ")


def score_pronunciation(target: str, spoken: str) -> dict:
    """Berechnet Aussprache-Score. Gibt {'score': 0-100, 'grade': str, 'feedback': str, 'word': str} zurueck."""
    t = _normalize(target)
    s = _normalize(spoken)

    if not s:
        return {"score": 0, "grade": "try_again", "feedback": "Nichts erkannt. Bitte nochmal versuchen.", "word": target}

    ratio = difflib.SequenceMatcher(None, t, s).ratio()
    score = int(ratio * 100)
    if t == s:
        score = 100

    if score >= 90:
        grade, feedback = "perfect", "Perfekt! \U0001f3af"
    elif score >= 70:
        grade, feedback = "good", "Sehr gut! \U0001f44d"
    elif score >= 50:
        grade, feedback = "ok", "Gut, aber noch etwas Uebung. \U0001f4aa"
    else:
        grade, feedback = "try_again", "Nochmal bitte! \U0001f501"

    if t != s and score < 90:
        diff_hints = []
        for tw, sw in zip(t.split(), s.split()):
            if tw != sw:
                diff_hints.append(f"'{sw}' \u2192 '{tw}'")
        if diff_hints:
            feedback += f"\n\U0001f4ac Korrektur: {', '.join(diff_hints[:2])}"

    return {"score": score, "grade": grade, "feedback": feedback, "word": target}


def evaluate_pronunciation(target: str, spoken: str) -> dict:
    """Bewertet Aussprache. Gibt {'score', 'grade', 'feedback', 'word'} zurueck.

    grade-Werte: 'perfect' | 'good' | 'ok' | 'try_again'
    """
    return score_pronunciation(target, spoken)


def format_feedback(result: dict, teacher: str) -> str:
    """Formatiert Ergebnis-Nachricht fuer Telegram.
    Enthaelt immer das Zielwort (word) im Output.
    """
    score = result["score"]
    grade = result.get("grade", "")
    feedback = result.get("feedback", "")
    word = result.get("word", "")

    bars = int(score / 10)
    bar = "\U0001f7e9" * bars + "\u2b1c" * (10 - bars)

    # Zielwort immer prominent einbinden
    base = (
        f"\U0001f3a4 *Aussprache-Ergebnis*\n\n"
        f"{bar} {score}/100\n"
        f"Bewertung: *{grade.upper()}*\n\n"
        f"*{word}*: {feedback}"
    )

    if score < 60:
        tips = {
            "vitali":    "\n\n\U0001f4a1 Tipp: Hoer dir das Wort nochmal an!",
            "dering":    "\n\n\U0001f4a1 Nochmal ueben.",
            "imperator": "\n\n\U0001f525 Inakzeptabel. Nochmal.",
        }
        base += tips.get(teacher, tips["vitali"])

    return base


def build_pronounce_prompt(word_de: str, teacher: str) -> str:
    prompts = {
        "vitali":    f"\U0001f3a4 Sprich dieses Wort auf Deutsch:\n\n*{word_de}*\n\nSchick mir eine Sprachnachricht!",
        "dering":    f"\U0001f3a4 Sprich: *{word_de}*",
        "imperator": f"\U0001f525 AUSSPRACHE-TRAINING:\n*{word_de}*\n\nJetzt sprechen!",
    }
    return prompts.get(teacher, prompts["vitali"])


def build_result_message(word_de: str, result: dict, teacher: str) -> str:
    return format_feedback(result, teacher)
