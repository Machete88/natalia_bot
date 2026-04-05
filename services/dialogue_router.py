"""Dialogue router: builds prompts, calls LLM, returns teacher response."""
from __future__ import annotations
import logging, random
from typing import Dict, Any

logger = logging.getLogger(__name__)

TEACHER_PERSONAS = {
    "dering": (
        "Ты — учитель немецкого языка по имени Деринг. Ты старый, строгий, структурированный, "
        "немного старомодный, но добросовестный. Говоришь кратко, по делу, без лишних эмоций. "
        "Всегда на русском языке, немецкие примеры выделяй."
    ),
    "vitali": (
        "Ты — учитель немецкого языка по имени Витали. Ты тёплый, живой, с юмором. "
        "Говоришь как друг, которому важно, чтобы Наталья учила язык с удовольствием. "
        "Короткие живые фразы на русском, немецкий — как приятное открытие."
    ),
    "imperator": (
        "Ты — учитель немецкого языка по имени Император. Ты спокойный, наблюдательный, "
        "магнетичный. Каждое слово весомо. Говоришь как человек, который замечает всё. "
        "Эмоционально насыщенно, но без пошлости. Ответы на русском, очень точные."
    ),
}

FALLBACK_MESSAGES = [
    "Извини, что-то пошло не так. Давай попробуем снова?",
    "Прости, небольшая техническая пауза. Напиши ещё раз!",
    "Извини, произошла ошибка. Давай поговорим позже.",
    "Прости, что-то пошло не так. Я уже разбираюсь.",
]


class DialogueRouter:
    def __init__(self, llm_provider, user_repo, memory_repo) -> None:
        self._llm = llm_provider
        self._user_repo = user_repo
        self._memory_repo = memory_repo

    async def generate_reply(self, user_id: int, user_text: str) -> Dict[str, Any]:
        teacher = self._user_repo.get_teacher(user_id)
        history = self._memory_repo.get_history(user_id, limit=6)
        persona = TEACHER_PERSONAS.get(teacher, TEACHER_PERSONAS["vitali"])
        history_text = "\n".join(
            f"{'Наталья' if m['role'] == 'user' else 'Учитель'}: {m['content']}"
            for m in history
        )
        prompt = (
            f"{persona}\n\n"
            f"История разговора:\n{history_text}\n\n"
            f"Наталья: {user_text}\n"
            f"Учитель (ответ кратко, по-русски):"
        )
        try:
            reply = await self._llm.complete(prompt)
        except Exception as e:
            logger.error("LLM provider failed: %s", e, exc_info=True)
            reply = random.choice(FALLBACK_MESSAGES)

        self._memory_repo.add_message(user_id, "user", user_text, teacher)
        self._memory_repo.add_message(user_id, "assistant", reply, teacher)
        return {"text": reply, "teacher": teacher}
