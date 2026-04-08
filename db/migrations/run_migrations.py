"""Fuehrt alle ausstehenden Migrationen in der richtigen Reihenfolge aus.

Usage:
    python -m db.migrations.run_migrations
    # oder:
    python db/migrations/run_migrations.py
"""
from __future__ import annotations

import os
import sqlite3
import sys

MIGRATIONS = [
    ("002_sm2_fields.sql", [
        "ALTER TABLE vocab_progress ADD COLUMN ease_factor REAL NOT NULL DEFAULT 2.5",
        "ALTER TABLE vocab_progress ADD COLUMN interval_days INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE vocab_progress ADD COLUMN repetitions INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE vocab_progress ADD COLUMN next_review_date TEXT",
    ]),
]


def run(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for name, statements in MIGRATIONS:
            for sql in statements:
                try:
                    conn.execute(sql)
                    print(f"[OK]  {name}: {sql[:60]}")
                except sqlite3.OperationalError as exc:
                    if "duplicate column" in str(exc).lower():
                        print(f"[SKIP] {name}: Spalte existiert bereits")
                    else:
                        print(f"[ERR] {name}: {exc}")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, "data", "natalia.db")
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    print(f"Datenbank: {db_path}")
    run(db_path)
    print("Fertig.")
