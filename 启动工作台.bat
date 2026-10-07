@echo off
chcp 65001 >nul
title StylePack 工作台
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
  python web\launch.py
  goto end
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 web\launch.py
  goto end
)
echo 未找到 Python：请安装 Python 3.9+（https://www.python.org/downloads/）后重试
:end
pause
