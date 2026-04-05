=== NataliaBot Windows Quickstart ===

1. Python 3.11+ installieren: https://www.python.org
   -> "Add Python to PATH" anhaeken!

2. Projektordner nach C:\NataliaBot kopieren

3. PowerShell als Admin oeffnen:
   cd C:\NataliaBot
   .\ops\windows\install_windows.ps1

4. API-Keys eintragen:
   notepad C:\NataliaBot\.env

5. Bot starten:
   .\ops\windows\start_bot.ps1

6. Tests ausfuehren:
   .venv\Scripts\python -m pytest tests\ -v

=== Notwendige Keys ===
TELEGRAM_BOT_TOKEN  -> @BotFather in Telegram
AUTHORIZED_USER_ID  -> deine Telegram-ID (@userinfobot)
ADMIN_USER_ID       -> Admin-Telegram-ID
OPENAI_API_KEY      -> https://openrouter.ai
ELEVENLABS_API_KEY  -> https://elevenlabs.io
