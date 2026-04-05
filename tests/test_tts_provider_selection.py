from unittest.mock import patch
from config.settings import Settings
from services.runtime_init import initialise_services

def test_selects_mock_tts_when_not_configured(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("AUTHORIZED_USER_ID", "1")
    monkeypatch.setenv("ADMIN_USER_ID", "2")
    monkeypatch.setenv("TTS_PROVIDER", "mock")
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    with patch("config.settings._load_dotenv", return_value=None):
        settings = Settings.from_env()
    services = initialise_services(settings)
    from services.tts import MockTTSProvider
    assert isinstance(services["tts"], MockTTSProvider)
