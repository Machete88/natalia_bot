# NataliaBot Windows Installer
$ProjectDir = "C:\NataliaBot"
Write-Host "=== NataliaBot Windows Install ===" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[FEHLER] Python nicht gefunden. Installiere Python 3.10+ von https://www.python.org" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ProjectDir)) {
    New-Item -ItemType Directory -Path $ProjectDir | Out-Null
}

cd $ProjectDir

if (-not (Test-Path "$ProjectDir\.venv")) {
    Write-Host "[INFO] Erstelle virtuelle Umgebung..." -ForegroundColor Yellow
    python -m venv .venv
}

& "$ProjectDir\.venv\Scripts\pip" install --upgrade pip --quiet
& "$ProjectDir\.venv\Scripts\pip" install -r requirements.txt --quiet

if (-not (Test-Path "$ProjectDir\.env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[WICHTIG] Trage deine API-Keys in C:\NataliaBot\.env ein!" -ForegroundColor Yellow
}

foreach ($d in @("data","logs","media\audio","media\cache","media\stickers")) {
    New-Item -ItemType Directory -Path "$ProjectDir\$d" -Force | Out-Null
}

Write-Host "[OK] Installation abgeschlossen!" -ForegroundColor Green
Write-Host "Starte mit: .\start_bot.ps1" -ForegroundColor Cyan
