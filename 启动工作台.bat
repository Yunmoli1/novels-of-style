@echo off
chcp 65001 >nul
title StylePack 工作台
cd /d "%~dp0"

rem 优先 python，验证可用（防 WindowsApps 占位 stub），失败再试 py -3
where python >nul 2>nul
if %errorlevel%==0 (
  python -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    python web\launch.py %*
    goto end
  )
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 web\launch.py %*
  goto end
)
echo Python not found. Please install Python 3.9+ from https://www.python.org/downloads/
:end
pause
