import pytest
from unittest.mock import patch
from config.settings import Settings

def test_missing_mandatory_variables(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("AUTHORIZED_USER_ID", raising=False)
    monkeypatch.delenv("ADMIN_USER_ID", raising=False)
    with patch("config.settings._load_dotenv", return_value=None):
        with pytest.raises(RuntimeError):
            Settings.from_env()

def test_loading_with_defaults(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy")
    monkeypatch.setenv("AUTHORIZED_USER_ID", "1")
    monkeypatch.setenv("ADMIN_USER_ID", "2")
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    with patch("config.settings._load_dotenv", return_value=None):
        settings = Settings.from_env()
    assert settings.telegram_bot_token == "dummy"
    assert settings.authorized_user_id == 1
    assert settings.llm_provider == "openai"
    assert settings.database_path.endswith("natalia_bot.db")
