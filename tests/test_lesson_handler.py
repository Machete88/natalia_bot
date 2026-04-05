"""Tests fuer /lesson Handler."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


@dataclass
class FakeVocabStep:
    vocab_id: int
    word_de: str
    word_ru: str
    example_de: str
    example_ru: str
    type: str = "new_vocab"


@pytest.fixture
def fake_services():
    user_repo = MagicMock()
    user_repo.get_or_create_user.return_value = 1
    user_repo.get_teacher.return_value = "vitali"

    lesson_planner = MagicMock()
    lesson_planner.next_steps.return_value = [
        FakeVocabStep(1, "Hallo", "Привет", "Hallo, wie geht es dir?", "Привет, как дела?"),
        FakeVocabStep(2, "Danke", "Спасибо", "Danke sehr!", "Большое спасибо!"),
    ]
    return {"user_repo": user_repo, "lesson_planner": lesson_planner, "tts": None, "voice_pipeline": None}


@pytest.mark.asyncio
async def test_lesson_sends_vocab_message(fake_services):
    from bot.handlers.lesson import handle_lesson

    update = MagicMock()
    update.effective_user.id = 111
    update.effective_user.first_name = "Natasha"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []
    context.bot_data = {"services": fake_services}

    await handle_lesson(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args[0][0]
    assert "Hallo" in call_args
    assert "Danke" in call_args


@pytest.mark.asyncio
async def test_lesson_empty_state(fake_services):
    from bot.handlers.lesson import handle_lesson

    fake_services["lesson_planner"].next_steps.return_value = []

    update = MagicMock()
    update.effective_user.id = 111
    update.effective_user.first_name = "Natasha"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []
    context.bot_data = {"services": fake_services}

    await handle_lesson(update, context)
    update.message.reply_text.assert_called_once()
