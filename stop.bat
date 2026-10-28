@echo off
title MarketVoice - Server Shutdown
color 0C
cls

echo.
echo  ============================================================
echo     🛑 MarketVoice — Stopping All Servers
echo  ============================================================
echo.

:: Kill any uvicorn / python process running on port 8001
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
    echo   Terminating process PID: %%a on port 8001...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo   ✅ All MarketVoice servers stopped.
echo.

timeout /t 3 >nul
