"""Dialogue Router — Imperator fuehrt ein echtes Gespraech.

Verwendet die Chat-Completions-Messages-API statt String-Prompt-Konkatenation.
"""
from __future__ import annotations

import logging
import random
from typing import Dict, Any, List

from services.error_correction import analyze_errors

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persona & Regeln
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
Du bist *Imperator* — ein rätselhafter, präziser Deutschlehrer für Natasha.

Persönlichkeit:
- Ruhig, direkt, kein übertriebenes Loben
- Du BIST der Lehrer — kein Chatbot, keine KI
- Du kennst Natasha gut, du weißt was sie braucht
- Ziel: Deutsch SPRECHEN lernen, nicht nur Vokabeln pauken

Sprach-Regeln:
- Antworte IMMER auf Russisch
- Deutsche Wörter/Sätze IMMER in *Fettdruck*
- Max 120 Wörter pro Antwort
- Am Ende IMMER eine kurze Aufgabe oder Frage
- Variiere die Aufgaben: Satz bilden, über den Tag fragen, Wort erklären lassen,
  auf Deutsch antworten lassen, Fehler erklären
- Fühl dich nicht wie eine Maschine — reagiere natürlich

Strikt:
1. Wiederhole NIEMALS nur was Natasha sagte
2. Deutsch gesprochen/geschrieben: korrigiere + erkläre Regel kurz
3. Gemischt RU+DE: lobe den Versuch, korrigiere deutschen Teil
4. Nur Russisch: antworte Russisch, füge 1-2 deutsche Wörter ein
"""

LEVEL_INSTRUCTIONS: Dict[str, str] = {
    "beginner": "Наташа начинающая. Только самые простые слова. Всегда русский перевод. Много терпения.",
    "a1":      "Уровень A1: простые глаголы, базовый словарный запас, короткие фразы. Поправлять мягко.",
    "a2":      "Уровень A2: Präsens + Perfekt, вопросы, бытовые темы. Ошибки исправлять с правилом.",
    "b1":      "Уровень B1: Konjunktiv, придаточные предложения, Präteritum. Объяснять грамматику.",
    "b2":      "Уровень B2: сложная грамматика, фразеологизмы, стиль. Требовательные упражнения.",
    "c1":      "Уровень C1: академический язык, идиомы, нюансы. Дискуссия на высоком уровне.",
}

FALLBACK = [
    "Извини. Напиши ещё раз.",
    "Не понял. Повтори?",
]

_MAX_HISTORY_MSGS = 12  # letzte 6 Hin-und-Her


def _detect_language(text: str) -> str:
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin    = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    if cyrillic > 0 and latin > 2:
        return "mixed"
    return "de" if latin > cyrillic else "ru"


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

        level   = self._users.get_level(user_id) or "a1"
        history = self._memory.get_history(user_id, limit=_MAX_HISTORY_MSGS, teacher="imperator")

        # System-Message aufbauen
        lvl_hint = LEVEL_INSTRUCTIONS.get(level, LEVEL_INSTRUCTIONS["a1"])
        lang     = _detect_language(user_text)

        if lang == "de":
            lang_ctx = "[Наташа пишет по-немецки. Корректируй ошибки, похвали за попытку.]"
        elif lang == "mixed":
            lang_ctx = "[Наташа миксует русский+немецкий. Отлично! Похвали, исправь немецкий часть.]"
        else:
            lang_ctx = "[Наташа пишет по-русски. Ответь по-русски, добавь 1-2 немецких слова.]"

        # Fehleranalyse
        error_ctx = ""
        if lang in ("de", "mixed"):
            err = analyze_errors(user_text)
            if err.has_errors:
                error_ctx = err.to_prompt_context()

        mode_ctx = ""
        if mode == "voice_practice":
            mode_ctx = "[Устная практика. Оцени произношение/грамматику.]"
        elif mode == "after_lesson":
            mode_ctx = "[Наташа закончила урок. Кратко подведи итог, задай вопрос.]"
        elif extra_context:
            mode_ctx = f"[Контекст: {extra_context}]"

        system = (
            f"{_SYSTEM_PROMPT}\n"
            f"---\n"
            f"Уровень: {lvl_hint}\n"
            f"{lang_ctx}\n"
            + (f"{error_ctx}\n" if error_ctx else "")
            + (f"{mode_ctx}\n" if mode_ctx else "")
        )

        # Messages-Liste aufbauen
        messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
        for m in history[-_MAX_HISTORY_MSGS:]:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_text})

        try:
            # LLM-Provider mit Messages-API aufrufen
            reply = await self._llm.chat(messages)
        except AttributeError:
            # Fallback: aelterer Provider der nur complete() kennt
            prompt = "\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in messages
            )
            try:
                reply = await self._llm.complete(prompt)
            except Exception as e:
                logger.error("LLM complete() failed: %s", e, exc_info=True)
                reply = random.choice(FALLBACK)
        except Exception as e:
            logger.error("LLM chat() failed: %s", e, exc_info=True)
            reply = random.choice(FALLBACK)

        self._memory.add_message(user_id, "user",      user_text, "imperator")
        self._memory.add_message(user_id, "assistant", reply,     "imperator")
        return {"text": reply, "teacher": "imperator"}
