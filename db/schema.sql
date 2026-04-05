CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    name TEXT,
    language_level TEXT DEFAULT 'beginner',
    teacher TEXT DEFAULT 'vitali',
    created_at TEXT DEFAULT (datetime('now')),
    last_seen TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    key TEXT NOT NULL,
    value TEXT,
    UNIQUE(user_id, key)
);

CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    teacher TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    topic TEXT,
    score INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Vocabulary items for structured learning
CREATE TABLE IF NOT EXISTS vocab_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    topic TEXT NOT NULL,
    word_de TEXT NOT NULL,
    word_ru TEXT NOT NULL,
    example_de TEXT,
    example_ru TEXT
);

-- User-specific vocabulary progress (spaced repetition)
CREATE TABLE IF NOT EXISTS vocab_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    vocab_id INTEGER NOT NULL REFERENCES vocab_items(id),
    status TEXT NOT NULL DEFAULT 'new', -- new/learning/mastered
    correct_streak INTEGER NOT NULL DEFAULT 0,
    last_seen TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, vocab_id)
);

-- Homework submissions (photos / documents)
CREATE TABLE IF NOT EXISTS homework_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    file_path TEXT NOT NULL,
    extracted_text TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    checked INTEGER NOT NULL DEFAULT 0
);
