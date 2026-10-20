@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
echo ==============================================
echo MulKAnaliz - ilk kurulum
echo ==============================================
where py >nul 2>nul
if errorlevel 1 (
  echo HATA: Python Launcher bulunamadi. Python 3.12 x64 kurun: https://www.python.org/downloads/release/python-31210/
  pause
  exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
  echo HATA: Node.js bulunamadi. Node.js LTS kurup tekrar deneyin.
  pause
  exit /b 1
)
cd /d "%ROOT%backend"
rem Always use Python 3.12. Recreate a virtual environment made with another version.
if exist ".venv\Scripts\python.exe" (
  set "MULK_PYVER="
  for /f "delims=" %%V in ('".venv\Scripts\python.exe" -c "import sys; print(sys.version_info[0]*100+sys.version_info[1])"') do set "MULK_PYVER=%%V"
  if not "!MULK_PYVER!"=="312" (
    echo Mevcut sanal ortam Python surumu uygun degil. Python 3.12 ortami yeniden olusturuluyor...
    rmdir /s /q .venv
  )
)
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo HATA: Python 3.12 bulunamadi. Python 3.12 x64 kurup tekrar deneyin.
    goto fail
  )
)
echo [1/4] Backend paketleri yukleniyor...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo [2/4] Veritabani migration'lari uygulaniyor...
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 goto fail
cd /d "%ROOT%frontend"
echo [3/4] Frontend paketleri yukleniyor...
call npm install
if errorlevel 1 goto fail
echo [4/4] Kurulum tamamlandi.
echo Uygulamayi baslatmak icin BASLAT.bat dosyasini calistirin.
pause
exit /b 0
:fail
echo.
echo Kurulum sirasinda hata olustu. Yukaridaki hata mesajini kontrol edin.
pause
exit /b 1
