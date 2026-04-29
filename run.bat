@echo off
REM Pipeline complet : fetch LBC -> upsert Supabase -> enrichit via Claude
REM Par defaut, ne traite QUE les watches VTT (enduro + DH France).
REM
REM Usage:
REM   run.bat                  -> VTT uniquement, enrichissement hybride
REM   run.bat opus             -> VTT uniquement, tout Opus
REM   run.bat haiku            -> VTT uniquement, tout Haiku
REM   run.bat all              -> TOUS les watches du config (VTT + voitures + motos)
REM   run.bat all opus         -> tous les watches, mode Opus

set PYTHON=C:\Python313\python.exe
set FIRST=%1
set SECOND=%2
set SCOPE=vtt
set MODE=hybrid

REM Premier argument peut etre 'all' (scope) ou un mode (opus/haiku/hybrid)
if /I "%FIRST%"=="all" (
  set SCOPE=all
  if not "%SECOND%"=="" set MODE=%SECOND%
) else (
  if not "%FIRST%"=="" set MODE=%FIRST%
)

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
echo === [2/3] Scraping LBC (scope: %SCOPE%) ===
if /I "%SCOPE%"=="vtt" (
  "%PYTHON%" -m scraper.main --watch vtt-enduro-france
  if errorlevel 1 ( echo Scraper VTT enduro failed. & pause & exit /b 1 )
  "%PYTHON%" -m scraper.main --watch vtt-dh-france
  if errorlevel 1 ( echo Scraper VTT DH failed. & pause & exit /b 1 )
) else (
  "%PYTHON%" -m scraper.main
  if errorlevel 1 ( echo Scraper failed. & pause & exit /b 1 )
)

echo.
echo === [3/3] Enriching pending ads via Claude (mode: %MODE%) ===
if /I "%MODE%"=="hybrid" (
  "%PYTHON%" -m scraper.enricher --hybrid --limit 500
) else (
  "%PYTHON%" -m scraper.enricher --model %MODE% --limit 500
)

echo.
echo === DONE ===
echo Open the web UI: start-web.bat
pause
