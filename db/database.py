"""Database initialisation."""
from __future__ import annotations
import sqlite3
from pathlib import Path


def initialise_database(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    schema = Path(__file__).parent / "schema.sql"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


# Alias fuer Rueckwaertskompatibilitaet
init_db = initialise_database
