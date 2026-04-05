"""Tests fuer /teacher Handler."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def fake_services():
    user_repo = MagicMock()
    user_repo.get_or_create_user.return_value = 1
    user_repo.get_teacher.return_value = "vitali"
    return {"user_repo": user_repo, "tts": None, "voice_pipeline": None}


@pytest.mark.asyncio
async def test_teacher_switch_valid(fake_services):
    from bot.handlers.teacher import handle_teacher

    update = MagicMock()
    update.effective_user.id = 111
    update.effective_user.first_name = "Natasha"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["dering"]
    context.bot_data = {"services": fake_services}

    await handle_teacher(update, context)

    fake_services["user_repo"].set_teacher.assert_called_once_with(1, "dering")
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_teacher_switch_invalid_shows_help(fake_services):
    from bot.handlers.teacher import handle_teacher

    update = MagicMock()
    update.effective_user.id = 111
    update.effective_user.first_name = "Natasha"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["unknown_teacher"]
    context.bot_data = {"services": fake_services}

    await handle_teacher(update, context)
    call_text = update.message.reply_text.call_args[0][0]
    assert "vitali" in call_text


@pytest.mark.asyncio
async def test_teacher_no_args_shows_help(fake_services):
    from bot.handlers.teacher import handle_teacher

    update = MagicMock()
    update.effective_user.id = 111
    update.effective_user.first_name = "Natasha"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []
    context.bot_data = {"services": fake_services}

    await handle_teacher(update, context)
    call_text = update.message.reply_text.call_args[0][0]
    assert "/teacher" in call_text
