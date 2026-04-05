"""Dialogue router: builds prompts, calls LLM, returns teacher response."""
from __future__ import annotations
import logging, random
from typing import Dict, Any

logger = logging.getLogger(__name__)

TEACHER_PERSONAS = {
    "dering": (
        "Du bist ein Deutschlehrer namens Dering. Du bist alt, streng, strukturiert, "
        "etwas altmodisch aber gewissenhaft. Du sprichst kurz und sachlich, ohne überfl\u00fc\u00dfige Emotionen. "
        "Antworte immer auf Russisch, deutsche Beispiele deutlich hervorheben. "
        "Du erinnerst dich an alle fr\u00fcheren Gespr\u00e4che mit Natasha."
    ),
    "vitali": (
        "Du bist ein Deutschlehrer namens Vitali. Du bist warm, lebendig, humorvoll. "
        "Du sprichst wie ein Freund, dem es wichtig ist, dass Natasha die Sprache mit Freude lernt. "
        "Kurze lebhafte S\u00e4tze auf Russisch, Deutsch als angenehme Entdeckung. "
        "Du erinnerst dich an alle fr\u00fcheren Gespr\u00e4che mit Natasha."
    ),
    "imperator": (
        "Du bist ein Deutschlehrer namens Imperator. Du bist ruhig, beobachtend, "
        "magnetisch. Jedes Wort hat Gewicht. Du sprichst wie jemand, der alles bemerkt. "
        "Emotional intensiv, aber niemals banal. Antworten auf Russisch, sehr pr\u00e4zise. "
        "Du erinnerst dich an alle fr\u00fcheren Gespr\u00e4che mit Natasha."
    ),
}

FALLBACK_MESSAGES = [
    "\u0418\u0437\u0432\u0438\u043d\u0438, \u0447\u0442\u043e-\u0442\u043e \u043f\u043e\u0448\u043b\u043e \u043d\u0435 \u0442\u0430\u043a. \u0414\u0430\u0432\u0430\u0439 \u043f\u043e\u043f\u0440\u043e\u0431\u0443\u0435\u043c \u0441\u043d\u043e\u0432\u0430?",
    "\u041f\u0440\u043e\u0441\u0442\u0438, \u043d\u0435\u0431\u043e\u043b\u044c\u0448\u0430\u044f \u0442\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u043f\u0430\u0443\u0437\u0430. \u041d\u0430\u043f\u0438\u0448\u0438 \u0435\u0449\u0451 \u0440\u0430\u0437!",
    "\u0418\u0437\u0432\u0438\u043d\u0438, \u043f\u0440\u043e\u0438\u0437\u043e\u0448\u043b\u0430 \u043e\u0448\u0438\u0431\u043a\u0430. \u0414\u0430\u0432\u0430\u0439 \u043f\u043e\u0433\u043e\u0432\u043e\u0440\u0438\u043c \u043f\u043e\u0437\u0436\u0435.",
]


class DialogueRouter:
    def __init__(self, llm_provider, user_repo, memory_repo) -> None:
        self._llm = llm_provider
        self._user_repo = user_repo
        self._memory_repo = memory_repo

    async def generate_reply(self, user_id: int, user_text: str) -> Dict[str, Any]:
        teacher = self._user_repo.get_teacher(user_id)
        level = self._user_repo.get_level(user_id)

        history = self._memory_repo.get_history(
            user_id, limit=12, teacher=teacher
        )

        persona = TEACHER_PERSONAS.get(teacher, TEACHER_PERSONAS["vitali"])

        # Backslash in f-string vermeiden (Python < 3.12 kompatibel)
        history_lines = []
        for m in history:
            speaker = "\u041dаташа" if m["role"] == "user" else "\u0423читель"
            history_lines.append(f"{speaker}: {m['content']}")
        history_text = "\n".join(history_lines)

        level_hint = (
            f"Natashas aktuelles Deutschniveau: {level.upper()}. "
            f"Passe die Erkl\u00e4rungen und deutschen Beispiele entsprechend an."
        )

        prompt = (
            f"{persona}\n\n"
            f"{level_hint}\n\n"
            f"Gespr\u00e4chsverlauf (nur mit dir, {teacher}):\n"
            f"{history_text}\n\n"
            f"Natasha: {user_text}\n"
            f"Lehrer (kurz, auf Russisch):"
        )

        try:
            reply = await self._llm.complete(prompt)
        except Exception as e:
            logger.error("LLM provider failed: %s", e, exc_info=True)
            reply = random.choice(FALLBACK_MESSAGES)

        self._memory_repo.add_message(user_id, "user", user_text, teacher)
        self._memory_repo.add_message(user_id, "assistant", reply, teacher)
        return {"text": reply, "teacher": teacher}
