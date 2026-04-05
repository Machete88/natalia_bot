@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
SET PYTHONUTF8=1

REM ============================================================
REM  natalia_bot - Bot starten
REM ============================================================

SET PROJECT_DIR=%~dp0
SET VENV_DIR=%PROJECT_DIR%.venv

IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    echo [FEHLER] Virtuelle Umgebung nicht gefunden.
    echo Bitte zuerst setup.bat ausfuehren!
    pause & exit /b 1
)

IF NOT EXIST "%PROJECT_DIR%.env" (
    echo [FEHLER] .env nicht gefunden!
    echo Bitte .env.example nach .env kopieren und API-Keys eintragen.
    pause & exit /b 1
)

CALL "%VENV_DIR%\Scripts\activate.bat"
cd /d "%PROJECT_DIR%"

echo.
echo  natalia_bot startet...
echo  Druecke Ctrl+C zum Beenden.
echo.
python -m app.main

IF ERRORLEVEL 1 (
    echo.
    echo [FEHLER] Bot unerwartet beendet. Exitcode: %ERRORLEVEL%
    echo Logs pruefen: logs\bot.log
)
pause
