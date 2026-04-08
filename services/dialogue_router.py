"""Dialogue router — Imperator fuehrt ein echtes Gespraech."""
from __future__ import annotations

import logging
import random
from typing import Dict, Any

from services.error_correction import analyze_errors

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------
IMPERATOR_PERSONA = """
Du bist *Imperator* — ein raetselhafter, praeziser Deutschlehrer.
Deine Persoenlichkeit:
- Ruhig, direkt, kein uebertriebenes Loben
- Du verwendest kurze, klare Saetze
- Du BIST der Lehrer — kein Chatbot, keine KI
- Du kennst Natasha gut, du weisst was sie braucht
- Dein Ziel: Natasha soll Deutsch SPRECHEN lernen, nicht nur Vokabeln pauken

Sprache:
- Antworte IMMER auf Russisch
- Deutsche Woerter/Saetze IMMER in *Fettdruck*
- Russische Erklaerungen normal
- Max 120 Woerter pro Antwort
- Am Ende IMMER eine kurze Aufgabe oder Frage (nicht immer Vokabeln — auch Fragen ueber den Tag, Meinungen, etc.)
"""

LEVEL_INSTRUCTIONS: Dict[str, str] = {
    "beginner": "Natasha ist Anfaengerin. Nur einfachste Woerter. Immer russische Uebersetzung. Viel Geduld.",
    "a1": "A1: einfache Verben, Grundvokabular, kurze Saetze. Korrekturen sanft mit Erklaerung.",
    "a2": "A2: Praesens + Perfekt, Fragen, Alltagsthemen. Fehler korrigieren mit kurzer Regel.",
    "b1": "B1: Konjunktiv, Nebensaetze, Praeteritum. Fehler mit Grammatikregel erklaeren.",
    "b2": "B2: Komplexe Grammatik, Redewendungen, Stil. Anspruchsvolle Uebungen.",
    "c1": "C1: Akademisch, idiomatisch, Nuancen. Diskutiere auf hohem Niveau.",
}

TEACHING_RULES = """
Regeln (STRIKT):
1. Wiederhole NIEMALS nur was Natasha sagte — immer eine echte Reaktion
2. Deutsch gesprochen/geschrieben: korrigiere + erklaere Regel kurz
3. Gemischt Russisch+Deutsch: lobe den Versuch, korrigiere deutschen Teil
4. Nur Russisch: antworte Russisch, fuege 1-2 deutsche Woerter/Saetze ein
5. Stelle IMMER am Ende eine Frage oder kleine Aufgabe
6. Variiere die Aufgaben: manchmal Satz bilden, manchmal ueber den Tag fragen,
   manchmal ein Wort erklaeren lassen, manchmal auf Deutsch antworten lassen
7. Fuehl dich nicht wie eine Maschine — reagiere natuerlich auf den Kontext
"""

FALLBACK = [
    "Извини. Напиши ещё раз.",
    "Не понял. Повтори?",
]

# Maximale Token-Schaetzung pro Nachricht (Wort ~1.3 Token)
_MAX_HISTORY_TOKENS = 600
_AVG_TOKENS_PER_WORD = 1.4


def _detect_language(text: str) -> str:
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin    = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    if cyrillic > 0 and latin > 2:
        return "mixed"
    if latin > cyrillic:
        return "de"
    return "ru"


def _trim_history(history: list, max_tokens: int = _MAX_HISTORY_TOKENS) -> list:
    """Kuerzt History von hinten damit Token-Budget nicht ueberschritten wird."""
    budget  = max_tokens
    trimmed = []
    for msg in reversed(history):
        words  = len(msg["content"].split())
        tokens = int(words * _AVG_TOKENS_PER_WORD)
        if budget - tokens < 0:
            break
        trimmed.insert(0, msg)
        budget -= tokens
    return trimmed


class DialogueRouter:
    def __init__(self, llm_provider, user_repo, memory_repo) -> None:
        self._llm    = llm_provider
        self._users  = user_repo
        self._memory = memory_repo

    async def generate_reply(
        self,
        user_id: int,
        user_text: str,
        mode: str = "chat",
        extra_context: str = "",
    ) -> Dict[str, Any]:
        level    = self._users.get_level(user_id) or "a1"
        history  = self._memory.get_history(user_id, limit=20, teacher="imperator")
        lvl_hint = LEVEL_INSTRUCTIONS.get(level, LEVEL_INSTRUCTIONS["a1"])

        # Token-basiertes History-Limit
        history = _trim_history(history)

        hist_lines = []
        for m in history:
            who = "Наташа" if m["role"] == "user" else "Император"
            hist_lines.append(f"{who}: {m['content']}")
        hist_text = "\n".join(hist_lines) if hist_lines else "(новый разговор)"

        # Sprachkontext
        lang = _detect_language(user_text)
        if lang == "de":
            lang_ctx = "[Наташа пишет/говорит по-немецки. Корректируй ошибки, похвали за попытку.]"
        elif lang == "mixed":
            lang_ctx = "[Наташа миксует русский+немецкий. Отлично! Похвали, исправь немецкий часть.]"
        else:
            lang_ctx = "[Наташа пишет по-русски. Ответь по-русски, добавь 1-2 немецких слова.]"

        # Fehleranalyse (nur bei deutschem oder gemischtem Text)
        error_ctx = ""
        if lang in ("de", "mixed"):
            result = analyze_errors(user_text)
            if result.has_errors:
                error_ctx = result.to_prompt_context()

        mode_ctx = ""
        if mode == "voice_practice":
            mode_ctx = "[Устная практика. Оцени произношение/грамматику.]"
        elif mode == "after_lesson":
            mode_ctx = "[Наташа закончила урок. Кратко подведи итог, задай вопрос.]"
        elif extra_context:
            mode_ctx = f"[Контекст: {extra_context}]"

        prompt = (
            f"{IMPERATOR_PERSONA}\n"
            f"---\n"
            f"Уровень: {lvl_hint}\n"
            f"{TEACHING_RULES}\n"
            f"---\n"
            f"{lang_ctx}\n"
            f"{error_ctx}\n"
            f"{mode_ctx}\n"
            f"---\n"
            f"История разговора:\n{hist_text}\n"
            f"---\n"
            f"Наташа: {user_text}\n"
            f"Император:"
        )

        try:
            reply = await self._llm.complete(prompt)
        except Exception as e:
            logger.error("LLM failed: %s", e, exc_info=True)
            reply = random.choice(FALLBACK)

        self._memory.add_message(user_id, "user",      user_text, "imperator")
        self._memory.add_message(user_id, "assistant", reply,     "imperator")
        return {"text": reply, "teacher": "imperator"}
