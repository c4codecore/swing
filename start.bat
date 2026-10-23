@echo off
title QUANTUM SWING - Server Launcher
color 0B
cls

echo.
echo  ============================================================
echo     ⚡ QUANTUM // AETHER — NSE Systematic Trading Studio
echo  ============================================================
echo.
echo  [1] Building latest frontend...
echo.

cd /d "%~dp0frontend"
call npm run build >nul 2>&1
echo       ✅ Frontend build complete.

echo.
echo  [2] Starting FastAPI Backend Server (port 8001)...
echo.

cd /d "%~dp0"

:: Get local IP for display
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr "192.168"') do (
    set LOCAL_IP=%%a
)
set LOCAL_IP=%LOCAL_IP: =%

echo       🖥️  This PC:     http://127.0.0.1:8001
echo       📱  LAN Access:  http://%LOCAL_IP%:8001
echo.
echo  ============================================================
echo   Open the above URL on any device connected to same WiFi
echo   Press Ctrl+C to stop the server
echo  ============================================================
echo.

cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

pause
