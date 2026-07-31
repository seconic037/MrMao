@echo off
cd /d "%~dp0"
echo 启动主席模拟器...
start "" http://localhost:8000
python run_server.py
pause
