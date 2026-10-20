@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%backend\.venv\Scripts\python.exe" (
  echo Ilk once KURULUM.bat dosyasini calistirin.
  pause
  exit /b 1
)
if not exist "%ROOT%frontend\node_modules\.bin\nuxt.cmd" (
  echo Frontend bagimliliklari bulunamadi. Ilk once KURULUM.bat dosyasini calistirin.
  pause
  exit /b 1
)
cd /d "%ROOT%backend"
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
  echo Veritabani migration'i basarisiz oldu; sunucular baslatilmadi.
  pause
  exit /b 1
)
start "MulKAnaliz Backend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%ROOT%backend'; & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
start "MulKAnaliz Frontend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%ROOT%frontend'; npm run dev"
timeout /t 3 /nobreak >nul
start "" "http://localhost:3000"
