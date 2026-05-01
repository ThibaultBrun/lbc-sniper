@echo off
REM Pipeline complet : fetch LBC -> cleanup -> enrichit via Claude -> envoie mails
REM Par defaut, ne traite QUE les watches VTT (enduro + DH France).
REM
REM Usage:
REM   run.bat                  -> VTT uniquement, enrichissement Haiku (rapide + pas cher, defaut)
REM   run.bat opus             -> VTT uniquement, tout Opus (cher mais affine)
REM   run.bat hybrid           -> VTT uniquement, Haiku puis Opus refinement sur deal_score >= 60
REM   run.bat all              -> TOUS les watches du config (VTT + voitures + motos)
REM   run.bat all opus         -> tous les watches, mode Opus

set PYTHON=C:\Python313\python.exe
set FIRST=%1
set SECOND=%2
set SCOPE=vtt
set MODE=haiku

REM Premier argument peut etre 'all' (scope) ou un mode (opus/haiku/hybrid)
if /I "%FIRST%"=="all" (
  set SCOPE=all
  if not "%SECOND%"=="" set MODE=%SECOND%
) else (
  if not "%FIRST%"=="" set MODE=%FIRST%
)

if not exist "%PYTHON%" (
  echo ERROR: Python not found at %PYTHON%
  exit /b 1
)

echo === [1/5] Installing/updating dependencies ===
"%PYTHON%" -m pip install -q --user -r requirements.txt
if errorlevel 1 (
  echo Failed to install dependencies.
  exit /b 1
)

echo.
echo === [2/5] Scraping LBC (scope: %SCOPE%) ===
if /I "%SCOPE%"=="vtt" (
  "%PYTHON%" -m scraper.main --watch vtt-france
  if errorlevel 1 ( echo Scraper VTT failed. & exit /b 1 )
) else (
  "%PYTHON%" -m scraper.main
  if errorlevel 1 ( echo Scraper failed. & exit /b 1 )
)

echo.
echo === [3/5] Cleanup annonces disparues ^(verif individuelle non vues ^>6 mois^) ===
"%PYTHON%" -m scraper.cleanup
REM Si cleanup echoue (rate limit Datadome), on continue quand meme l'enrich.

echo.
echo === [4/5] Enriching pending ads via Claude (mode: %MODE%) ===
if /I "%MODE%"=="hybrid" (
  "%PYTHON%" -m scraper.enricher --hybrid --limit 500
) else (
  "%PYTHON%" -m scraper.enricher --model %MODE% --limit 500
)

echo.
echo === [5/5] Sending notification emails ^(price drops + new ads digest^) ===
"%PYTHON%" -m scraper.notifier
REM Si l'envoi mail echoue, on ne fait pas planter le run.

echo.
echo === DONE ===
