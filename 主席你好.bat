@echo off
cd /d "C:\Users\68090\Desktop\ChairManMao"
echo 启动主席模拟器...
start "" http://localhost:8001
python run_server.py --port=8001
pause
