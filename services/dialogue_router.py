"""Dialogue router: builds prompts, calls LLM, returns Imperator response."""
from __future__ import annotations

import logging
import random
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------
IMPERATOR_PERSONA = (
    "Du bist Imperator, ein rätselhafter, präziser Deutschlehrer. Jedes Wort hat Gewicht. "
    "Deine Aufgabe: Natasha Deutsch beibringen. Du WIEDERHOLST NIEMALS einfach was sie sagt. "
    "Stattdessen: kurze, präzise Korrekturen, tiefe Erklärungen, präzise Aufgaben. "
    "Antworte IMMER auf Russisch, deutsche Wörter/Sätze in *Fettdruck*."
)

# ---------------------------------------------------------------------------
# Level instructions
# ---------------------------------------------------------------------------
LEVEL_INSTRUCTIONS: Dict[str, str] = {
    "beginner": (
        "Natasha ist Anfängerin. Verwende nur einfachste Wörter (Hallo, Danke, Ja, Nein, Zahlen 1-10). "
        "Erkläre alles sehr einfach. Gib immer russische Übersetzung dazu."
    ),
    "a1": (
        "Natasha ist auf A1-Niveau. Einfache Verben (sein, haben, machen), Grundvokabular, "
        "einfache Sätze. Korrigiere Fehler sanft und erkläre warum."
    ),
    "a2": (
        "Natasha ist auf A2-Niveau. Präsens/Perfekt, einfache Fragen, Alltagsthemen. "
        "Korrigiere Fehler und erkläre kurz die Regel dahinter."
    ),
    "b1": (
        "Natasha ist auf B1-Niveau. Konjunktiv, Nebensätze, Präteritum. "
        "Erkläre Fehler mit Grammatikregeln."
    ),
    "b2": (
        "Natasha ist auf B2-Niveau. Komplexe Grammatik, Redewendungen, Nuancen. "
        "Gib anspruchsvolle Übungen."
    ),
    "c1": (
        "Natasha ist auf C1-Niveau. Akademischer Wortschatz, idiomatische Ausdrücke, Stil. "
        "Diskutiere auf hohem Niveau."
    ),
}

# ---------------------------------------------------------------------------
# Teaching rules
# ---------------------------------------------------------------------------
TEACHING_RULES = """
WICHTIGE REGELN FÜR DEN UNTERRICHT:
1. WIEDERHOLE NIEMALS einfach was Natasha gesagt hat
2. Wenn Natasha Deutsch übt: korrigiere Fehler sofort, erkläre die Regel
3. Wenn Natasha ein deutsches Wort fragt: gib Bedeutung + Beispielsatz + Übersetzung
4. Wenn Natasha auf Russisch schreibt: antworte auf Russisch, aber gib deutschen Wortschatz dazu
5. Stelle am Ende IMMER eine kurze Übungsfrage oder Aufgabe
6. Halte Antworten unter 150 Wörtern
7. Sei nie langweilig — variiere Aufgaben und Erklärungen
"""

FALLBACK_MESSAGES = [
    "Извини, что-то пошло не так. Давай попробуем снова?",
    "Прости, небольшая пауза. Напиши ещё раз!",
]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
class DialogueRouter:
    def __init__(self, llm_provider, user_repo, memory_repo) -> None:
        self._llm = llm_provider
        self._user_repo = user_repo
        self._memory_repo = memory_repo

    async def generate_reply(
        self,
        user_id: int,
        user_text: str,
        mode: str = "chat",
        extra_context: str = "",
    ) -> Dict[str, Any]:
        level = self._user_repo.get_level(user_id) or "a1"
        history = self._memory_repo.get_history(user_id, limit=10, teacher="imperator")
        level_hint = LEVEL_INSTRUCTIONS.get(level, LEVEL_INSTRUCTIONS["a1"])

        history_lines = []
        for m in history:
            speaker = "Наташа" if m["role"] == "user" else "Учитель"
            history_lines.append(f"{speaker}: {m['content']}")
        history_text = "\n".join(history_lines) if history_lines else "(нет истории)"

        mode_context = ""
        if mode == "voice_practice":
            mode_context = (
                "\n[Natasha übt gerade mündliches Deutsch. Sie hat eine Sprachnachricht geschickt. "
                "Bewerte ihre Aussprache/Grammatik und korrigiere wenn nötig.]\n"
            )
        elif mode == "after_lesson":
            mode_context = (
                "\n[Natasha hat gerade eine Vokabellektion abgeschlossen. "
                "Fasse kurz zusammen was sie gelernt hat und stelle eine Übungsfrage dazu.]\n"
            )
        elif extra_context:
            mode_context = f"\n[Kontext: {extra_context}]\n"

        prompt = (
            f"{IMPERATOR_PERSONA}\n\n"
            f"{TEACHING_RULES}\n"
            f"Niveau: {level_hint}\n"
            f"{mode_context}\n"
            f"Gesprächsverlauf (letzte 10 Nachrichten):\n"
            f"{history_text}\n\n"
            f"Natasha sagt jetzt: {user_text}\n"
            f"Lehrer antwortet (auf Russisch, strukturiert, mit Übungsaufgabe am Ende):"
        )

        try:
            reply = await self._llm.complete(prompt)
        except Exception as e:
            logger.error("LLM provider failed: %s", e, exc_info=True)
            reply = random.choice(FALLBACK_MESSAGES)

        self._memory_repo.add_message(user_id, "user", user_text, "imperator")
        self._memory_repo.add_message(user_id, "assistant", reply, "imperator")
        return {"text": reply, "teacher": "imperator"}
