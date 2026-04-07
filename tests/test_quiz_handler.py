"""Tests fuer /quiz Handler und Quiz-Session."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.handlers.quiz import QuizSession, QUIZ_SESSION_KEY


@pytest.fixture
def fake_services():
    user_repo = MagicMock()
    user_repo.get_or_create_user.return_value = 1
    user_repo.get_teacher.return_value = "vitali"
    user_repo.get_level.return_value = "beginner"
    return {"user_repo": user_repo}


@pytest.fixture
def fake_settings(tmp_path):
    settings = MagicMock()
    db_path = str(tmp_path / "test.db")
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE vocab_items (id INTEGER PRIMARY KEY, level TEXT, topic TEXT, word_de TEXT, word_ru TEXT, example_de TEXT, example_ru TEXT)")
        conn.execute("CREATE TABLE vocab_progress (id INTEGER PRIMARY KEY, user_id INTEGER, vocab_id INTEGER, status TEXT DEFAULT 'new', correct_streak INTEGER DEFAULT 0, last_seen TEXT, UNIQUE(user_id, vocab_id))")
        for i, w in enumerate([("beginner","greetings","Hallo","\u041f\u0440\u0438\u0432\u0435\u0442","Hi","Hi"), ("beginner","greetings","Danke","\u0421\u043f\u0430\u0441\u0438\u0431\u043e","Danke!","Danke!"), ("beginner","feelings","muede","\u0443\u0441\u0442\u0430\u043b","Ich bin muede","Ich bin muede"), ("beginner","family","Mutter","\u043c\u0430\u043c\u0430","Meine Mutter","Meine Mutter")]):
            conn.execute("INSERT INTO vocab_items (level,topic,word_de,word_ru,example_de,example_ru) VALUES (?,?,?,?,?,?)", w)
    settings.database_path = db_path
    return settings


@pytest.mark.asyncio
async def test_quiz_sends_question(fake_services, fake_settings):
    from bot.handlers.quiz import handle_quiz

    update = MagicMock()
    update.effective_user.id = 111
    update.effective_user.first_name = "Natasha"
    update.message.text = "/quiz"
    update.message.reply_text = AsyncMock()
    update.callback_query = None  # kein Inline-Callback
    context = MagicMock()
    context.args = []
    context.user_data = {}
    context.bot_data = {"services": fake_services, "settings": fake_settings}

    await handle_quiz(update, context)

    update.message.reply_text.assert_called_once()
    assert QUIZ_SESSION_KEY in context.user_data


@pytest.mark.asyncio
async def test_quiz_correct_answer(fake_services, fake_settings):
    from bot.handlers.quiz import handle_quiz, QuizSession

    session = QuizSession(
        vocab_id=1,
        word_de="Hallo",
        word_ru="\u041f\u0440\u0438\u0432\u0435\u0442",
        example_de="Hallo!",
        correct_answer="Hallo",
        options=["Hallo", "Danke", "Bitte", "muede"],
        score=0,
        total=0,
    )

    update = MagicMock()
    update.effective_user.id = 111
    update.effective_user.first_name = "Natasha"
    update.message.text = "1"  # erste Option = Hallo = korrekt
    update.message.reply_text = AsyncMock()
    update.callback_query = None  # kein Inline-Callback
    context = MagicMock()
    context.user_data = {QUIZ_SESSION_KEY: session}
    context.bot_data = {"services": fake_services, "settings": fake_settings}

    await handle_quiz(update, context)
    assert update.message.reply_text.call_count >= 1
    first_call = update.message.reply_text.call_args_list[0][0][0]
    assert "\u2705" in first_call
