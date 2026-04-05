# NataliaBot Linux Quickstart

## Setup
```bash
chmod +x ops/linux/setup_natalia_bot.sh
./ops/linux/setup_natalia_bot.sh
nano /opt/natalia_bot/.env
```

## Starten
```bash
sudo systemctl start natalia-bot
sudo systemctl status natalia-bot
journalctl -u natalia-bot -f
```

## Tests
```bash
cd /opt/natalia_bot
.venv/bin/python -m pytest tests/ -v
```

## Notwendige Keys
- `TELEGRAM_BOT_TOKEN` → @BotFather
- `AUTHORIZED_USER_ID` → @userinfobot
- `OPENAI_API_KEY` → https://openrouter.ai
- `ELEVENLABS_API_KEY` → https://elevenlabs.io
