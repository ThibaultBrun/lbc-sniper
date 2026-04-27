@echo off
REM Pipeline complet : fetch LBC -> upsert Supabase -> enrichit via Claude
REM Usage: double-clic ou ".\run.bat" depuis cmd
REM Options: ".\run.bat haiku" pour utiliser Haiku au lieu d'Opus

set PYTHON=C:\Python313\python.exe
set MODEL=%1
if "%MODEL%"=="" set MODEL=opus

if not exist "%PYTHON%" (
  echo ERROR: Python not found at %PYTHON%
  pause
  exit /b 1
)

echo === [1/3] Installing/updating dependencies ===
"%PYTHON%" -m pip install -q --user -r requirements.txt
if errorlevel 1 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)

echo.
echo === [2/3] Scraping LBC ===
"%PYTHON%" -m scraper.main
if errorlevel 1 (
  echo Scraper failed.
  pause
  exit /b 1
)

echo.
echo === [3/3] Enriching new ads via Claude (model: %MODEL%) ===
"%PYTHON%" -m scraper.enricher --model %MODEL%

echo.
echo === DONE ===
echo Open the web UI: cd web && npm run dev
pause
