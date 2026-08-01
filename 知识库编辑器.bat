@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   MrMao 知识库编辑器（独立桌面应用）
echo ========================================
python tools/kb_editor.py
if errorlevel 1 (
  echo.
  echo   [错误] 启动失败，请确认已安装 Python 3.11
  pause
)
