"""Tests fuer den Support-Modus."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.handlers.support import (
    SUPPORT_MODE_KEY,
    SUPPORT_CHAT_ID_KEY,
    is_support_active,
)


@pytest.fixture
def fake_settings():
    s = MagicMock()
    s.support_codeword = "hilfe123"
    s.authorized_user_id = 111
    s.admin_user_id = 999
    return s


@pytest.fixture
def fake_services():
    user_repo = MagicMock()
    user_repo.get_or_create_user.return_value = 1
    user_repo.get_teacher.return_value = "vitali"
    return {"user_repo": user_repo}


def test_support_not_active_by_default():
    context = MagicMock()
    context.application.bot_data = {}
    assert is_support_active(context) is False


def test_support_active_when_flag_set():
    context = MagicMock()
    context.application.bot_data = {SUPPORT_MODE_KEY: True}
    assert is_support_active(context) is True


@pytest.mark.asyncio
async def test_codeword_activates_support(fake_settings, fake_services):
    from bot.handlers.support import activate_support

    update = MagicMock()
    update.effective_user.id = 111
    update.effective_user.first_name = "Natalia"
    update.effective_chat.id = 111
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.application.bot_data = {}
    context.bot_data = {"services": fake_services, "settings": fake_settings}
    context.bot.send_message = AsyncMock()

    await activate_support(update, context)

    assert context.application.bot_data.get(SUPPORT_MODE_KEY) is True
    assert context.application.bot_data.get(SUPPORT_CHAT_ID_KEY) == 111
    update.message.reply_text.assert_called_once()
    context.bot.send_message.assert_called_once()
    call_text = context.bot.send_message.call_args[1]["text"]
    assert "Support" in call_text


@pytest.mark.asyncio
async def test_admin_reply_forwarded_to_natalia(fake_settings, fake_services):
    from bot.handlers.support import handle_admin_reply

    update = MagicMock()
    update.effective_user.id = 999
    update.message.text = "Alles gut, kein Problem!"

    context = MagicMock()
    context.application.bot_data = {
        SUPPORT_MODE_KEY: True,
        SUPPORT_CHAT_ID_KEY: 111,
    }
    context.bot_data = {"services": fake_services, "settings": fake_settings}
    context.bot.send_message = AsyncMock()

    await handle_admin_reply(update, context)

    context.bot.send_message.assert_called_once()
    call_kwargs = context.bot.send_message.call_args[1]
    assert call_kwargs["chat_id"] == 111
    assert "Alles gut" in call_kwargs["text"]


@pytest.mark.asyncio
async def test_deactivate_support_clears_flag(fake_settings, fake_services):
    from bot.handlers.support import deactivate_support

    update = MagicMock()
    context = MagicMock()
    context.application.bot_data = {
        SUPPORT_MODE_KEY: True,
        SUPPORT_CHAT_ID_KEY: 111,
    }
    context.bot_data = {"services": fake_services, "settings": fake_settings}
    context.bot.send_message = AsyncMock()

    await deactivate_support(update, context)

    assert context.application.bot_data.get(SUPPORT_MODE_KEY) is False
    assert context.application.bot_data.get(SUPPORT_CHAT_ID_KEY) is None
