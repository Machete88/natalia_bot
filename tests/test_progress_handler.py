"""Tests fuer /progress Handler."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def fake_services_and_settings(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "test.db")
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS vocab_items (
                id INTEGER PRIMARY KEY, level TEXT, topic TEXT,
                word_de TEXT, word_ru TEXT, example_de TEXT, example_ru TEXT
            );
            CREATE TABLE IF NOT EXISTS vocab_progress (
                id INTEGER PRIMARY KEY, user_id INTEGER, vocab_id INTEGER,
                status TEXT DEFAULT 'new', correct_streak INTEGER DEFAULT 0,
                last_seen TEXT, UNIQUE(user_id, vocab_id)
            );
            CREATE TABLE IF NOT EXISTS streaks (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL UNIQUE,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_date TEXT
            );
        """)
        conn.execute("INSERT INTO vocab_items VALUES (1,'beginner','greetings','Hallo','Привет','Hi','Hi')")
        conn.execute("INSERT INTO vocab_progress (user_id,vocab_id,status,correct_streak) VALUES (1,1,'learning',1)")

    user_repo = MagicMock()
    user_repo.get_or_create_user.return_value = 1
    user_repo.get_teacher.return_value = "imperator"

    settings = MagicMock()
    settings.database_path = db_path

    return {"user_repo": user_repo}, settings


@pytest.mark.asyncio
async def test_progress_sends_stats(fake_services_and_settings):
    from bot.handlers.progress import handle_progress

    services, settings = fake_services_and_settings

    update = MagicMock()
    update.effective_user.id = 111
    update.effective_user.first_name = "Natasha"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.bot_data = {"services": services, "settings": settings}

    await handle_progress(update, context)

    update.message.reply_text.assert_called_once()
    msg = update.message.reply_text.call_args[0][0]
    assert "learning" in msg.lower() or "1" in msg
