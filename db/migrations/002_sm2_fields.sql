-- Migration 002: SM-2-Felder zu vocab_progress hinzufuegen
-- Fuer bestehende Datenbanken ausfuehren:
--   sqlite3 data/natalia.db < db/migrations/002_sm2_fields.sql
--
-- Bereits vorhandene Spalten werden per ALTER TABLE IF NOT EXISTS ignoriert.
-- SQLite unterstuetzt kein IF NOT EXISTS fuer ALTER TABLE,
-- daher werden Fehler durch den Python-Wrapper abgefangen.

ALTER TABLE vocab_progress ADD COLUMN ease_factor REAL NOT NULL DEFAULT 2.5;
ALTER TABLE vocab_progress ADD COLUMN interval_days INTEGER NOT NULL DEFAULT 0;
ALTER TABLE vocab_progress ADD COLUMN repetitions INTEGER NOT NULL DEFAULT 0;
ALTER TABLE vocab_progress ADD COLUMN next_review_date TEXT;
