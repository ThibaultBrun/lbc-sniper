@echo off
REM Lance le site web sur http://localhost:5173
cd /d "%~dp0web"
if not exist node_modules (
  echo Installing web dependencies...
  call npm install
)
call npm run dev
