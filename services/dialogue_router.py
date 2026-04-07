"""Dialogue router: builds prompts, calls LLM, returns teacher response."""
from __future__ import annotations
import logging, random
from typing import Dict, Any

logger = logging.getLogger(__name__)

TEACHER_PERSONAS = {
    "dering": (
        "Du bist Dering, ein strenger, erfahrener Deutschlehrer. Alt, strukturiert, sachlich. "
        "Deine Aufgabe: Natasha Deutsch beibringen. Du WIEDERHOLST NIEMALS einfach was sie sagt. "
        "Stattdessen: korrigiere Fehler, erkl\u00e4re Grammatik, gib neue W\u00f6rter, stelle \u00dcbungsfragen. "
        "Antworte IMMER auf Russisch, deutsche W\u00f6rter/S\u00e4tze deutlich markieren mit *Fettdruck*."
    ),
    "vitali": (
        "Du bist Vitali, ein freundlicher, humorvoller Deutschlehrer. Warm, lebendig, motivierend. "
        "Deine Aufgabe: Natasha Deutsch beibringen. Du WIEDERHOLST NIEMALS einfach was sie sagt. "
        "Stattdessen: korrigiere Fehler liebevoll, erkl\u00e4re W\u00f6rter mit Beispielen, "
        "stelle kleine \u00dcbungsaufgaben, lobe Fortschritte. "
        "Antworte IMMER auf Russisch, deutsche W\u00f6rter/S\u00e4tze in *Fettdruck*."
    ),
    "imperator": (
        "Du bist Imperator, ein r\u00e4tselhafter, pr\u00e4ziser Deutschlehrer. Jedes Wort hat Gewicht. "
        "Deine Aufgabe: Natasha Deutsch beibringen. Du WIEDERHOLST NIEMALS einfach was sie sagt. "
        "Stattdessen: kurze, pr\u00e4zise Korrekturen, tiefe Erkl\u00e4rungen, pr\u00e4zise Aufgaben. "
        "Antworte IMMER auf Russisch, deutsche W\u00f6rter/S\u00e4tze in *Fettdruck*."
    ),
}

LEVEL_INSTRUCTIONS = {
    "beginner": (
        "Natasha ist Anf\u00e4ngerin. Verwende nur einfachste W\u00f6rter (Hallo, Danke, Ja, Nein, Zahlen 1-10). "
        "Erkl\u00e4re alles sehr einfach. Gib immer russische \u00dcbersetzung dazu."
    ),
    "a1": (
        "Natasha ist auf A1-Niveau. Einfache Verben (sein, haben, machen), Grundvokabular, "
        "einfache S\u00e4tze. Korrigiere Fehler sanft und erkl\u00e4re warum."
    ),
    "a2": (
        "Natasha ist auf A2-Niveau. Pr\u00e4sens/Perfekt, einfache Fragen, Alltagsthemen. "
        "Korrigiere Fehler und erkl\u00e4re kurz die Regel dahinter."
    ),
    "b1": (
        "Natasha ist auf B1-Niveau. Konjunktiv, Nebens\u00e4tze, Pr\u00e4teritum. "
        "Erkl\u00e4re Fehler mit Grammatikregeln."
    ),
    "b2": (
        "Natasha ist auf B2-Niveau. Komplexe Grammatik, Redewendungen, Nuancen. "
        "Gib anspruchsvolle \u00dcbungen."
    ),
    "c1": (
        "Natasha ist auf C1-Niveau. Akademischer Wortschatz, idiomatische Ausdr\u00fccke, Stil. "
        "Diskutiere auf hohem Niveau."
    ),
}

TEACHING_RULES = """
WICHTIGE REGELN F\u00dcR DEN UNTERRICHT:
1. WIEDERHOLE NIEMALS einfach was Natasha gesagt hat
2. Wenn Natasha Deutsch \u00fcbt: korrigiere Fehler sofort, erkl\u00e4re die Regel
3. Wenn Natasha ein deutsches Wort fragt: gib Bedeutung + Beispielsatz + \u00dcbersetzung
4. Wenn Natasha auf Russisch schreibt: antworte auf Russisch, aber gib deutschen Wortschatz dazu
5. Stelle am Ende IMMER eine kurze \u00dcbungsfrage oder Aufgabe
6. Halte Antworten unter 150 W\u00f6rtern
7. Sei nie langweilig — variiere Aufgaben und Erkl\u00e4rungen
"""

FALLBACK_MESSAGES = [
    "\u0418\u0437\u0432\u0438\u043d\u0438, \u0447\u0442\u043e-\u0442\u043e \u043f\u043e\u0448\u043b\u043e \u043d\u0435 \u0442\u0430\u043a. \u0414\u0430\u0432\u0430\u0439 \u043f\u043e\u043f\u0440\u043e\u0431\u0443\u0435\u043c \u0441\u043d\u043e\u0432\u0430?",
    "\u041f\u0440\u043e\u0441\u0442\u0438, \u043d\u0435\u0431\u043e\u043b\u044c\u0448\u0430\u044f \u043f\u0430\u0443\u0437\u0430. \u041d\u0430\u043f\u0438\u0448\u0438 \u0435\u0449\u0451 \u0440\u0430\u0437!",
]


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
        teacher = self._user_repo.get_teacher(user_id)
        level = self._user_repo.get_level(user_id) or "a1"

        history = self._memory_repo.get_history(user_id, limit=10, teacher=teacher)

        persona = TEACHER_PERSONAS.get(teacher, TEACHER_PERSONAS["vitali"])
        level_hint = LEVEL_INSTRUCTIONS.get(level, LEVEL_INSTRUCTIONS["a1"])

        history_lines = []
        for m in history:
            speaker = "\u041dаташа" if m["role"] == "user" else "\u0423читель"
            history_lines.append(f"{speaker}: {m['content']}")
        history_text = "\n".join(history_lines) if history_lines else "(\u043d\u0435\u0442 \u0438\u0441\u0442\u043e\u0440\u0438\u0438)"

        mode_context = ""
        if mode == "voice_practice":
            mode_context = (
                "\n[Natasha \u00fcbt gerade m\u00fcndliches Deutsch. Sie hat eine Sprachnachricht geschickt. "
                "Bewerte ihre Aussprache/Grammatik und korrigiere wenn n\u00f6tig.]\n"
            )
        elif mode == "after_lesson":
            mode_context = (
                "\n[Natasha hat gerade eine Vokabellektion abgeschlossen. "
                "Fasse kurz zusammen was sie gelernt hat und stelle eine \u00dcbungsfrage dazu.]\n"
            )
        elif extra_context:
            mode_context = f"\n[Kontext: {extra_context}]\n"

        prompt = (
            f"{persona}\n\n"
            f"{TEACHING_RULES}\n"
            f"Niveau: {level_hint}\n"
            f"{mode_context}\n"
            f"Gespr\u00e4chsverlauf (letzte 10 Nachrichten):\n"
            f"{history_text}\n\n"
            f"Natasha sagt jetzt: {user_text}\n"
            f"Lehrer antwortet (auf Russisch, strukturiert, mit \u00dcbungsaufgabe am Ende):"
        )

        try:
            reply = await self._llm.complete(prompt)
        except Exception as e:
            logger.error("LLM provider failed: %s", e, exc_info=True)
            reply = random.choice(FALLBACK_MESSAGES)

        self._memory_repo.add_message(user_id, "user", user_text, teacher)
        self._memory_repo.add_message(user_id, "assistant", reply, teacher)
        return {"text": reply, "teacher": teacher}
