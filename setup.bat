@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
SET PYTHONUTF8=1

REM ============================================================
REM  natalia_bot - Windows Setup & Start
REM  Fuer Python 3.10+
REM ============================================================

SET PROJECT_DIR=%~dp0
SET VENV_DIR=%PROJECT_DIR%.venv
SET PYTHON=python

echo.
echo  natalia_bot - Setup
echo  ==================
echo  Projektpfad: %PROJECT_DIR%
echo.

REM -- Python pruefen
%PYTHON% --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [FEHLER] Python nicht gefunden!
    echo Download: https://www.python.org/downloads/
    pause & exit /b 1
)
echo [OK] Python gefunden:
%PYTHON% --version
echo.

REM -- Venv erstellen falls nicht vorhanden
IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] Erstelle virtuelle Umgebung...
    %PYTHON% -m venv "%VENV_DIR%"
    IF ERRORLEVEL 1 ( echo [FEHLER] Venv-Erstellung fehlgeschlagen. & pause & exit /b 1 )
    echo [OK] Virtuelle Umgebung erstellt.
) ELSE (
    echo [OK] Virtuelle Umgebung bereits vorhanden.
)

REM -- Venv aktivieren
CALL "%VENV_DIR%\Scripts\activate.bat"
echo [OK] Venv aktiviert.
echo.

REM -- Pip aktualisieren
python -m pip install --upgrade pip --quiet
echo [OK] pip aktualisiert.

REM -- Abhaengigkeiten installieren
IF EXIST "%PROJECT_DIR%requirements.txt" (
    echo [INFO] Installiere Abhaengigkeiten...
    pip install -r "%PROJECT_DIR%requirements.txt" --quiet
    echo [OK] Abhaengigkeiten installiert.
) ELSE (
    echo [WARNUNG] requirements.txt nicht gefunden!
)
echo.

REM -- .env pruefen
IF NOT EXIST "%PROJECT_DIR%.env" (
    echo [WARNUNG] .env nicht gefunden!
    echo Kopiere .env.example nach .env und trage deine API-Keys ein:
    echo   copy .env.example .env
    echo.
)

REM -- Verzeichnisse anlegen
IF NOT EXIST "%PROJECT_DIR%data" mkdir "%PROJECT_DIR%data"
IF NOT EXIST "%PROJECT_DIR%logs" mkdir "%PROJECT_DIR%logs"
IF NOT EXIST "%PROJECT_DIR%media\cache" mkdir "%PROJECT_DIR%media\cache"
IF NOT EXIST "%PROJECT_DIR%media\audio" mkdir "%PROJECT_DIR%media\audio"
IF NOT EXIST "%PROJECT_DIR%media\homework" mkdir "%PROJECT_DIR%media\homework"
IF NOT EXIST "%PROJECT_DIR%media\stickers" mkdir "%PROJECT_DIR%media\stickers"
echo [OK] Verzeichnisse angelegt.
echo.

REM -- pytest.ini pruefen
IF NOT EXIST "%PROJECT_DIR%pytest.ini" (
    echo [INFO] Erstelle pytest.ini...
    (
        echo [pytest]
        echo asyncio_mode = auto
    ) > "%PROJECT_DIR%pytest.ini"
    echo [OK] pytest.ini erstellt.
)

echo ============================================================
echo  Setup abgeschlossen!
echo ============================================================
echo.
echo Naechste Schritte:
echo  1. .env bearbeiten: notepad .env
echo  2. Bot starten:     python -m app.main
echo  3. Tests laufen:    python -m pytest tests\ -v
echo.
pause
