"""Tests fuer Streak-Tracking."""
from __future__ import annotations
import sqlite3
import pytest
from datetime import datetime, timedelta


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "streak_test.db")
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                UNIQUE(user_id, key)
            )
        """)
    return path


def test_first_streak(db_path):
    from services.reminder import update_streak
    streak = update_streak(db_path, user_id=1)
    assert streak == 1


def test_streak_increments_consecutive_days(db_path):
    from services.reminder import update_streak

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT OR REPLACE INTO user_preferences (user_id,key,value) VALUES (1,'last_learned',?)", (yesterday,))
        conn.execute("INSERT OR REPLACE INTO user_preferences (user_id,key,value) VALUES (1,'streak','3')")

    streak = update_streak(db_path, user_id=1)
    assert streak == 4


def test_streak_resets_after_gap(db_path):
    from services.reminder import update_streak

    old_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT OR REPLACE INTO user_preferences (user_id,key,value) VALUES (1,'last_learned',?)", (old_date,))
        conn.execute("INSERT OR REPLACE INTO user_preferences (user_id,key,value) VALUES (1,'streak','10')")

    streak = update_streak(db_path, user_id=1)
    assert streak == 1


def test_same_day_no_double_count(db_path):
    from services.reminder import update_streak

    streak1 = update_streak(db_path, user_id=1)
    streak2 = update_streak(db_path, user_id=1)
    assert streak1 == streak2
