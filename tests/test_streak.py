"""Tests fuer den Lern-Streak."""
from __future__ import annotations
import os
import pytest
import sqlite3
from datetime import date, timedelta


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "streak_test.db")
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                UNIQUE(user_id, key)
            );
        """)
    return path


def test_first_streak(db_path):
    from services.reminder import update_streak
    result = update_streak(db_path, user_id=1)
    assert result == 1


def test_streak_increments_consecutive_days(db_path):
    from services.reminder import update_streak
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    today = date.today().strftime("%Y-%m-%d")
    update_streak(db_path, user_id=1, today=yesterday)
    result = update_streak(db_path, user_id=1, today=today)
    assert result == 2


def test_streak_resets_after_gap(db_path):
    from services.reminder import update_streak
    old_date = (date.today() - timedelta(days=3)).strftime("%Y-%m-%d")
    today = date.today().strftime("%Y-%m-%d")
    update_streak(db_path, user_id=1, today=old_date)
    result = update_streak(db_path, user_id=1, today=today)
    assert result == 1


def test_same_day_no_double_count(db_path):
    from services.reminder import update_streak
    today = date.today().strftime("%Y-%m-%d")
    update_streak(db_path, user_id=1, today=today)
    result = update_streak(db_path, user_id=1, today=today)
    assert result == 1
