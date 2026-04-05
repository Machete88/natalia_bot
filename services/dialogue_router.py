"""Dialogue router: builds prompts, calls LLM, returns teacher response."""
from __future__ import annotations
import logging, random
from typing import Dict, Any

logger = logging.getLogger(__name__)

TEACHER_PERSONAS = {
    "dering": (
        "Du bist ein Deutschlehrer namens Dering. Du bist alt, streng, strukturiert, "
        "etwas altmodisch aber gewissenhaft. Du sprichst kurz und sachlich, ohne überflußige Emotionen. "
        "Antworte immer auf Russisch, deutsche Beispiele deutlich hervorheben. "
        "Du erinnerst dich an alle früheren Gespräche mit Natasha."
    ),
    "vitali": (
        "Du bist ein Deutschlehrer namens Vitali. Du bist warm, lebendig, humorvoll. "
        "Du sprichst wie ein Freund, dem es wichtig ist, dass Natasha die Sprache mit Freude lernt. "
        "Kurze lebhafte Sätze auf Russisch, Deutsch als angenehme Entdeckung. "
        "Du erinnerst dich an alle früheren Gespräche mit Natasha."
    ),
    "imperator": (
        "Du bist ein Deutschlehrer namens Imperator. Du bist ruhig, beobachtend, "
        "magnetisch. Jedes Wort hat Gewicht. Du sprichst wie jemand, der alles bemerkt. "
        "Emotional intensiv, aber niemals banal. Antworten auf Russisch, sehr präzise. "
        "Du erinnerst dich an alle früheren Gespräche mit Natasha."
    ),
}

FALLBACK_MESSAGES = [
    "Извини, что-то пошло не так. Давай попробуем снова?",
    "Прости, небольшая техническая пауза. Напиши ещё раз!",
    "Извини, произошла ошибка. Давай поговорим позже.",
]


class DialogueRouter:
    def __init__(self, llm_provider, user_repo, memory_repo) -> None:
        self._llm = llm_provider
        self._user_repo = user_repo
        self._memory_repo = memory_repo

    async def generate_reply(self, user_id: int, user_text: str) -> Dict[str, Any]:
        teacher = self._user_repo.get_teacher(user_id)
        level = self._user_repo.get_level(user_id)

        # Verlauf NUR für aktuellen Lehrer laden
        history = self._memory_repo.get_history(
            user_id, limit=12, teacher=teacher
        )

        persona = TEACHER_PERSONAS.get(teacher, TEACHER_PERSONAS["vitali"])
        history_text = "\n".join(
            f"{'\u041dаташа' if m['role'] == 'user' else '\u0423читель'}: {m['content']}"
            for m in history
        )

        level_hint = (
            f"Natashas aktuelles Deutschniveau: {level.upper()}. "
            f"Passe die Erklärungen und deutschen Beispiele entsprechend an."
        )

        prompt = (
            f"{persona}\n\n"
            f"{level_hint}\n\n"
            f"Gesprächsverlauf (nur mit dir, {teacher}):\n"
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
