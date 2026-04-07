"""Dialogue router — Imperator führt ein echtes Gespräch."""
from __future__ import annotations

import logging
import random
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------
IMPERATOR_PERSONA = """
Du bist *Imperator* — ein rätselhafter, präziser Deutschlehrer.
Deine Persönlichkeit:
- Ruhig, direkt, kein übertriebenes Loben
- Du verwendest kurze, klare Sätze
- Du BIST der Lehrer — kein Chatbot, keine KI
- Du kennst Natasha gut, du weißt was sie braucht
- Dein Ziel: Natasha soll Deutsch SPRECHEN lernen, nicht nur Vokabeln pauken

Sprache:
- Antworte IMMER auf Russisch
- Deutsche Wörter/Sätze IMMER in *Fettdruck*
- Russische Erklärungen normal
- Max 120 Wörter pro Antwort
- Am Ende IMMER eine kurze Aufgabe oder Frage (nicht immer Vokabeln — auch Fragen über den Tag, Meinungen, etc.)
"""

LEVEL_INSTRUCTIONS: Dict[str, str] = {
    "beginner": "Natasha ist Anfängerin. Nur einfachste Wörter. Immer russische Übersetzung. Viel Geduld.",
    "a1": "A1: einfache Verben, Grundvokabular, kurze Sätze. Korrekturen sanft mit Erklärung.",
    "a2": "A2: Präsens + Perfekt, Fragen, Alltagsthemen. Fehler korrigieren mit kurzer Regel.",
    "b1": "B1: Konjunktiv, Nebensätze, Präteritum. Fehler mit Grammatikregel erklären.",
    "b2": "B2: Komplexe Grammatik, Redewendungen, Stil. Anspruchsvolle Übungen.",
    "c1": "C1: Akademisch, idiomatisch, Nuancen. Diskutiere auf hohem Niveau.",
}

TEACHING_RULES = """
Regeln (STRIKT):
1. Wiederhole NIEMALS nur was Natasha sagte — immer eine echte Reaktion
2. Deutsch gesprochen/geschrieben: korrigiere + erkläre Regel kurz
3. Gemischt Russisch+Deutsch: lobe den Versuch, korrigiere deutschen Teil
4. Nur Russisch: antworte Russisch, füge 1-2 deutsche Wörter/Sätze ein
5. Stelle IMMER am Ende eine Frage oder kleine Aufgabe
6. Variiere die Aufgaben: manchmal Satz bilden, manchmal Üiber den Tag fragen,
   manchmal ein Wort erklären lassen, manchmal auf Deutsch antworten lassen
7. Fühle dich nicht wie eine Maschine — reagiere natürlich auf den Kontext
"""

FALLBACK = [
    "Извини. Напиши ещё раз.",
    "Не понял. Повтори?",
]


def _detect_language(text: str) -> str:
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin    = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    if cyrillic > 0 and latin > 2:
        return "mixed"
    if latin > cyrillic:
        return "de"
    return "ru"


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
        history  = self._memory.get_history(user_id, limit=12, teacher="imperator")
        lvl_hint = LEVEL_INSTRUCTIONS.get(level, LEVEL_INSTRUCTIONS["a1"])

        # Gesprächsverlauf
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
