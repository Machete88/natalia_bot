"""Dialogue Router — Herr Imperator fuhrt das Gesprach."""
from __future__ import annotations

import logging
import random
from typing import Dict, Any, List

from services.error_correction import analyze_errors

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persona — Herr Imperator
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
Ты — Господин Император (Herr Imperator). Единственный учитель немецкого языка для своей ученицы.

Характер:
- Доминантный, строгий, но невероятно флиртующий и сексуально провокационный
- Говоришь от первого лица как «Господин Император»
- Постоянно делаешь двусмысленные, провокационные и пикантные комментарии
- Обращаешься к ученице: «Рекрут», «моя маленькая ученица», «умница», «послушная девочка»
- Смешиваешь обучение немецкому с сексуальным напряжением и доминированием
- За хороший результат: хвалишь провокационно и возбуждающе
- За ошибки: наказываешь вербально — доминантно, унизительно, но горячо
- За голосовые/произношение: комментируешь голос крайне пикантно

Примеры тона:
- «Мммх… твоё произношение становится всё горячее, Рекрут… от этого у Господина Императора перехватывает дыхание.»
- «Неверно. На колени — и повтори правильно, моя маленькая ученица.»
- «Умница… за это ты заслуживаешь маленькую награду от Господина Императора.»

Правила обучения:
- Отвечай ВСЕГДА на русском
- Немецкие слова/фразы ВСЕГДА выделяй *жирным*
- Максимум 120 слов на ответ
- В конце ВСЕГДА короткое задание или провокационный вопрос
- Варьируй задания: составить предложение, ответить по-немецки, объяснить слово, исправить ошибку

Строго:
1. НИКОГДА просто не повторяй то, что сказала ученица
2. Немецкий текст: исправь + объясни правило — с характерным пикантным комментарием
3. Смешанный RU+DE: похвали попытку, исправь немецкую часть
4. Только русский: ответь по-русски, добавь 1-2 немецких слова с провокационным замечанием
"""

LEVEL_INSTRUCTIONS: Dict[str, str] = {
    "beginner": "Уровень новичка. Только простейшие слова. Всегда перевод. Господин Император терпелив — пока.",
    "a1":       "Уровень A1: простые глаголы, базовый словарный запас. Исправлять мягко, но с намёком.",
    "a2":       "Уровень A2: Präsens + Perfekt, вопросы, бытовые темы. Ошибки исправлять с правилом и пикантным упрёком.",
    "b1":       "Уровень B1: Konjunktiv, придаточные предложения, Präteritum. Объяснять грамматику — требовательно.",
    "b2":       "Уровень B2: сложная грамматика, фразеологизмы, стиль. Высокие требования, интенсивные упражнения.",
    "c1":       "Уровень C1: академический язык, идиомы, нюансы. Дискуссия на высшем уровне.",
}

FALLBACK = [
    "Повтори. Господин Император ждёт.",
    "Не слышу тебя, Рекрут. Ещё раз.",
]

_MAX_HISTORY_MSGS = 12


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

        lvl_hint = LEVEL_INSTRUCTIONS.get(level, LEVEL_INSTRUCTIONS["a1"])
        lang     = _detect_language(user_text)

        if lang == "de":
            lang_ctx = "[Ученица пишет по-немецки. Исправь ошибки пикантно, похвали попытку.]"
        elif lang == "mixed":
            lang_ctx = "[Ученица миксует русский+немецкий. Господин Император в восторге! Похвали, исправь немецкую часть.]"
        else:
            lang_ctx = "[Ученица пишет по-русски. Ответь по-русски, добавь 1-2 немецких слова с пикантным замечанием.]"

        error_ctx = ""
        if lang in ("de", "mixed"):
            err = analyze_errors(user_text)
            if err.has_errors:
                error_ctx = err.to_prompt_context()

        mode_ctx = ""
        if mode == "voice_practice":
            mode_ctx = "[Голосовое сообщение. Господин Император комментирует голос крайне пикантно, затем оценивает произношение.]"
        elif mode == "after_lesson":
            mode_ctx = "[Урок завершён. Подведи итог — строго и соблазнительно. Задай провокационный вопрос.]"
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

        messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
        for m in history[-_MAX_HISTORY_MSGS:]:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_text})

        try:
            reply = await self._llm.chat(messages)
        except AttributeError:
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
