@echo off
REM Pipeline complet : fetch LBC -> upsert Supabase -> enrichit via Claude
REM Usage:
REM   run.bat                  -> hybride (Haiku partout, Opus si deal_score >= 60)
REM   run.bat opus             -> tout Opus (lent, qualite max)
REM   run.bat haiku            -> tout Haiku (rapide, qualite moindre)

set PYTHON=C:\Python313\python.exe
set MODE=%1
if "%MODE%"=="" set MODE=hybrid

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
echo === [3/3] Enriching new ads via Claude (mode: %MODE%) ===
if /I "%MODE%"=="hybrid" (
  "%PYTHON%" -m scraper.enricher --hybrid --limit 500
) else (
  "%PYTHON%" -m scraper.enricher --model %MODE% --limit 500
)

echo.
echo === DONE ===
echo Open the web UI: start-web.bat
pause
