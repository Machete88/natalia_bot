import pytest
from unittest.mock import MagicMock, patch
from config.settings import Settings

@pytest.mark.asyncio
async def test_build_application_returns_app(monkeypatch):
    try:
        from bot.application import build_application
        from telegram.ext import Application as TgApp
    except ImportError:
        pytest.skip("telegram library not installed")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("AUTHORIZED_USER_ID", "1")
    monkeypatch.setenv("ADMIN_USER_ID", "2")
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    with patch("config.settings._load_dotenv", return_value=None):
        settings = Settings.from_env()
    from services.runtime_init import initialise_services
    services = initialise_services(settings)
    mock_app = MagicMock(spec=TgApp)
    mock_builder = MagicMock()
    mock_builder.token.return_value = mock_builder
    mock_builder.build.return_value = mock_app
    with patch.object(TgApp, "builder", return_value=mock_builder):
        app = await build_application(settings, services)
    assert app is mock_app
