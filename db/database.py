"""Datenbankinitialisierung fuer natalia_bot."""
from __future__ import annotations
import sqlite3
from pathlib import Path


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name        TEXT DEFAULT '',
                teacher     TEXT DEFAULT 'vitali',
                level       TEXT DEFAULT 'a1',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS vocabulary (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                russian     TEXT NOT NULL,
                german      TEXT NOT NULL,
                topic       TEXT DEFAULT 'general',
                level       TEXT DEFAULT 'a1'
            );

            CREATE TABLE IF NOT EXISTS user_vocabulary (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL REFERENCES users(id),
                vocab_id       INTEGER NOT NULL REFERENCES vocabulary(id),
                status         TEXT DEFAULT 'new',
                correct_streak INTEGER DEFAULT 0,
                last_seen      TIMESTAMP,
                UNIQUE(user_id, vocab_id)
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                telegram_id INTEGER NOT NULL,
                remind_time TEXT NOT NULL,
                active      INTEGER DEFAULT 1,
                UNIQUE(user_id)
            );

            CREATE TABLE IF NOT EXISTS conversation_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS streaks (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL UNIQUE,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_date      TEXT
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key     TEXT NOT NULL,
                value   TEXT,
                UNIQUE(user_id, key)
            );
        """)


# Alias fuer Rueckwaertskompatibilitaet mit Tests
def initialise_database(db_path: str) -> None:
    init_db(db_path)
