# natalia_bot 🇩🇪

Telegram-Bot zum Deutsch-Lernen fuer Natalia — mit KI-Lehrern, Vokabeltraining, Aussprache-Check und Support-Modus.

## Features

| Befehl | Funktion |
|---|---|
| `/start` | Begrüßung + Befehlsmenü |
| `/lesson` | 5 neue Vokabeln lernen |
| `/quiz` | Multiple-Choice Quiz |
| `/pronounce [Wort]` | Aussprache-Check (TTS + Whisper) |
| `/teacher vitali\|dering\|imperator` | KI-Lehrer wechseln |
| `/setlevel a1..c1` | Sprachlevel setzen |
| `/progress` | Statistik & Streak |
| Foto / Dokument | Hausaufgaben-Korrektur |
| Sprachnachricht | STT → Lehrer antwortet per TTS |
| Text | Freies Gespräch mit Lehrer |
| Codewort (z.B. `hilfe123`) | Support-Modus aktivieren |
| `/endsupport` | Support-Modus beenden |

## Setup (Windows)

```powershell
# 1. Repo klonen
git clone https://github.com/Machete88/natalia_bot.git
cd natalia_bot

# 2. Einmalig einrichten
setup.bat

# 3. .env konfigurieren
notepad .env

# 4. Bot starten
start.bat
```

## Setup (Docker)

```bash
cp .env.example .env
notepad .env  # Werte eintragen
docker compose up -d
docker compose logs -f
```

## Admin-Dashboard

```powershell
python admin/dashboard.py
# → http://localhost:5050
```

## Tests

```powershell
test.bat
# oder
pytest tests/ -v
```

## .env Pflichtfelder

```env
TELEGRAM_BOT_TOKEN=   # Bot-Token von @BotFather
AUTHORIZED_USER_ID=   # Telegram-ID von Natalia
ADMIN_USER_ID=        # Deine Telegram-ID
SUPPORT_CODEWORD=     # Geheimwort fuer Support-Modus
OPENAI_API_KEY=       # OpenAI / OpenRouter Key
```

## Projekt-Struktur

```
natalia_bot/
├── app/              # Bot-Einstiegspunkt
├── bot/handlers/     # Telegram-Handler
├── services/         # KI, STT, TTS, Reminder
├── config/           # Settings
├── content/          # Vokabellisten (JSON)
├── admin/            # Web-Dashboard (Flask)
├── tests/            # Pytest-Testsuite
├── .github/workflows/# CI/CD
├── Dockerfile
├── docker-compose.yml
├── setup.bat / start.bat / test.bat
└── .env.example
```

## KI-Lehrer

| Lehrer | Stil |
|---|---|
| **Vitali** | Warm, motivierend, Russisch-Deutsch gemischt |
| **Dering** | Professionell, strukturiert |
| **Imperator** | Streng, knapp, direkt |

## Vokabel-Level

`beginner` → `a1` → `a2` → `b1` → `b2` → `c1`

Level wird mit `/setlevel` gesetzt und beeinflusst `/lesson` und `/quiz`.

## Spaced Repetition

- 3× korrekt → Status `mastered` 🏆
- Falsch → Streak Reset → zurück auf `learning`
- Tägliche Erinnerung wenn noch nicht gelernt

## Lizenz

Privat / nicht öffentlich.
