"""Aussprache-Feedback: Nutzer spricht ein deutsches Wort,
Whisper transkribiert -> Bot vergleicht mit Zielwort -> bewertet.

Fluss:
1. /pronounce (oder nach /lesson automatisch) -> Bot schickt Zielwort + Mikrofon-Emoji
2. Natalia schickt Sprachnachricht
3. Bot transkribiert mit Whisper
4. Bot vergleicht phonetisch -> gibt Note + Feedback
"""
from __future__ import annotations
import logging
import os
import difflib
from typing import Optional

logger = logging.getLogger(__name__)

# Status-Key in context.user_data
PRONUNCE_KEY = "pronounce_target"


def _normalize(text: str) -> str:
    """Kleinschreiben, Sonderzeichen normalisieren."""
    text = text.lower().strip()
    replacements = {
        "ae": "ae", "oe": "oe", "ue": "ue",
        "\u00e4": "ae", "\u00f6": "oe", "\u00fc": "ue",
        "\u00df": "ss",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Nur Buchstaben behalten
    return "".join(c for c in text if c.isalpha() or c == " ")


def score_pronunciation(target: str, spoken: str) -> dict:
    """Berechnet Aussprache-Score.
    Gibt {'score': 0-100, 'grade': str, 'feedback': str} zurueck.
    """
    t = _normalize(target)
    s = _normalize(spoken)

    if not s:
        return {"score": 0, "grade": "F", "feedback": "Nichts erkannt. Bitte nochmal versuchen."}

    # Aehnlichkeit berechnen
    ratio = difflib.SequenceMatcher(None, t, s).ratio()
    score = int(ratio * 100)

    # Exakter Match (inkl. kleine Variationen)
    if t == s:
        score = 100

    # Note vergeben
    if score >= 90:
        grade, feedback = "A", "Perfekt! \U0001f3af"
    elif score >= 75:
        grade, feedback = "B", "Sehr gut! \U0001f44d"
    elif score >= 60:
        grade, feedback = "C", "Gut, aber noch etwas Uebung. \U0001f4aa"
    elif score >= 40:
        grade, feedback = "D", "Weiter ueben! \U0001f4da"
    else:
        grade, feedback = "F", "Nochmal bitte! \U0001f501"

    # Hinweis auf spezifische Unterschiede
    if t != s and score < 90:
        t_words = t.split()
        s_words = s.split()
        diff_hints = []
        for tw, sw in zip(t_words, s_words):
            if tw != sw:
                diff_hints.append(f"'{sw}' → '{tw}'")
        if diff_hints:
            feedback += f"\n\U0001f4ac Korrektur: {', '.join(diff_hints[:2])}"

    return {"score": score, "grade": grade, "feedback": feedback}


def build_pronounce_prompt(word_de: str, teacher: str) -> str:
    """Baut Aufforderungs-Nachricht zum Aussprechen."""
    prompts = {
        "vitali":    f"\U0001f3a4 Sprich dieses Wort auf Deutsch:\n\n*{word_de}*\n\nSchick mir eine Sprachnachricht!",
        "dering":    f"\U0001f3a4 Sprich: *{word_de}*",
        "imperator": f"\U0001f525 AUSSPRACHE-TRAINING:\n*{word_de}*\n\nJetzt sprechen!",
    }
    return prompts.get(teacher, prompts["vitali"])


def build_result_message(word_de: str, result: dict, teacher: str) -> str:
    """Baut Ergebnis-Nachricht."""
    score = result["score"]
    grade = result["grade"]
    feedback = result["feedback"]

    bars = int(score / 10)
    bar = "\U0001f7e9" * bars + "\u2b1c" * (10 - bars)

    base = (
        f"\U0001f3a4 *Aussprache von '{word_de}'*\n\n"
        f"{bar} {score}/100\n"
        f"Note: **{grade}**\n\n"
        f"{feedback}"
    )

    if score < 60:
        tips = {
            "vitali":    "\n\n\U0001f4a1 Tipp: Hoer dir das Wort nochmal an und versuch es erneut!",
            "dering":    "\n\n\U0001f4a1 Nochmal ueben.",
            "imperator": "\n\n\U0001f525 Inakzeptabel. Nochmal.",
        }
        base += tips.get(teacher, tips["vitali"])

    return base
