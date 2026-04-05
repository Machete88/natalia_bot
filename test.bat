@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
SET PYTHONUTF8=1

REM ============================================================
REM  natalia_bot - Tests ausfuehren
REM ============================================================

SET PROJECT_DIR=%~dp0
SET VENV_DIR=%PROJECT_DIR%.venv

IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    echo [FEHLER] Virtuelle Umgebung nicht gefunden.
    echo Bitte zuerst setup.bat ausfuehren!
    pause & exit /b 1
)

CALL "%VENV_DIR%\Scripts\activate.bat"
cd /d "%PROJECT_DIR%"

echo.
echo  natalia_bot - Tests
echo  ==================
echo.
python -m pytest tests\ -v --tb=short
SET EXIT=%ERRORLEVEL%
echo.
IF %EXIT% EQU 0 (
    echo [ERFOLG] Alle Tests bestanden!
) ELSE (
    echo [FEHLER] Einige Tests fehlgeschlagen. Exitcode: %EXIT%
)
echo.
pause
exit /b %EXIT%
