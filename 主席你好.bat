@echo off
cd /d "%~dp0"
setlocal

:: prefer project uv python, else PATH python
set "PYEXE=C:\Users\68090\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

:: if port 8000 already listening, server is running -> just open browser
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
if %errorlevel%==0 (
    echo [MrMao] server already running, opening browser...
    start "" http://localhost:8000
    exit /b 0
)

echo [MrMao] starting...
start "" http://localhost:8000
"%PYEXE%" run_server.py
pause
