@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM  setup_and_test.bat
REM  Projektordner: z.B. C:\natalia_bot
REM  Anpassen: PROJECT_DIR auf deinen tatsaechlichen Pfad setzen
REM ============================================================

SET PROJECT_DIR=C:\natalia_bot
SET VENV_DIR=%PROJECT_DIR%\.venv
SET PYTHON=python

echo ============================================================
echo  Windows Setup ^& Test Runner
echo  Projektpfad: %PROJECT_DIR%
echo ============================================================
echo.

REM -- 1. Python pruefen
%PYTHON% --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [FEHLER] Python nicht gefunden. Bitte Python 3.10+ installieren.
    echo         Download: https://www.python.org/downloads/
    pause & exit /b 1
)
echo [OK] Python gefunden:
%PYTHON% --version

REM -- 2. In Projektverzeichnis wechseln
IF NOT EXIST "%PROJECT_DIR%" (
    echo [FEHLER] Projektordner nicht gefunden: %PROJECT_DIR%
    echo         Bitte PROJECT_DIR in diesem Skript anpassen.
    pause & exit /b 1
)
cd /d "%PROJECT_DIR%"
echo [OK] Verzeichnis: %CD%

REM -- 3. Virtuelle Umgebung erstellen (falls nicht vorhanden)
IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] Erstelle virtuelle Umgebung...
    %PYTHON% -m venv "%VENV_DIR%"
    IF ERRORLEVEL 1 (
        echo [FEHLER] Virtuelle Umgebung konnte nicht erstellt werden.
        pause & exit /b 1
    )
    echo [OK] Virtuelle Umgebung erstellt: %VENV_DIR%
) ELSE (
    echo [OK] Virtuelle Umgebung bereits vorhanden.
)

REM -- 4. Venv aktivieren
CALL "%VENV_DIR%\Scripts\activate.bat"
echo [OK] Virtuelle Umgebung aktiviert.

REM -- 5. UTF-8 erzwingen (Kyrillisch/Unicode in Konsole)
SET PYTHONUTF8=1
chcp 65001 >nul
echo [OK] UTF-8 Konsole aktiviert (PYTHONUTF8=1).

REM -- 6. Pip aktualisieren
echo [INFO] Aktualisiere pip...
python -m pip install --upgrade pip --quiet

REM -- 7. Abhaengigkeiten installieren
IF EXIST "%PROJECT_DIR%\requirements.txt" (
    echo [INFO] Installiere Abhaengigkeiten aus requirements.txt...
    pip install -r "%PROJECT_DIR%\requirements.txt" --quiet
) ELSE (
    echo [INFO] Keine requirements.txt gefunden. Installiere Basispakete...
    pip install pytest pytest-asyncio python-telegram-bot aiohttp --quiet
)
pip install pytest pytest-asyncio --quiet
echo [OK] Abhaengigkeiten installiert.

REM -- 8. pytest.ini / pyproject.toml pruefen und ggf. erstellen
IF NOT EXIST "%PROJECT_DIR%\pytest.ini" (
    IF NOT EXIST "%PROJECT_DIR%\pyproject.toml" (
        echo [INFO] Erstelle pytest.ini fuer asyncio-Modus...
        (
            echo [pytest]
            echo asyncio_mode = auto
        ) > "%PROJECT_DIR%\pytest.ini"
        echo [OK] pytest.ini erstellt.
    )
)

REM -- 9. conftest.py: Windows asyncio EventLoop-Patch pruefen
findstr /C:"WindowsSelectorEventLoopPolicy" "%PROJECT_DIR%\tests\conftest.py" >nul 2>&1
IF ERRORLEVEL 1 (
    echo [INFO] Fuege Windows asyncio EventLoop-Patch zu conftest.py hinzu...
    python "%PROJECT_DIR%\patch_conftest.py" 2>nul
    IF ERRORLEVEL 1 (
        echo [WARNUNG] Patch konnte nicht automatisch angewendet werden.
        echo           Bitte manuell am Anfang von tests\conftest.py einfuegen:
        echo           import asyncio, sys
        echo           if sys.platform == "win32":
        echo               asyncio.set_event_loop_policy^(asyncio.WindowsSelectorEventLoopPolicy^(^)^)
    )
) ELSE (
    echo [OK] Windows asyncio EventLoop-Patch bereits vorhanden.
)

REM -- 10. media/cache Verzeichnis anlegen (MockTTSProvider)
IF NOT EXIST "%PROJECT_DIR%\media\cache" (
    mkdir "%PROJECT_DIR%\media\cache"
    echo [OK] Verzeichnis media\cache erstellt.
)

REM -- 11. Tests ausfuehren
echo.
echo ============================================================
echo  Starte pytest...
echo ============================================================
python -m pytest tests\ -v --tb=short
SET TEST_EXIT=%ERRORLEVEL%

echo.
IF %TEST_EXIT% EQU 0 (
    echo [ERFOLG] Alle Tests bestanden!
) ELSE (
    echo [FEHLER] Einige Tests sind fehlgeschlagen. Exitcode: %TEST_EXIT%
)

echo.
pause
exit /b %TEST_EXIT%
