@echo off
rem Windows 前台启动控制台（后台常驻请用 python start_daemons.py）
chcp 65001 >nul
cd /d %~dp0\..\console
echo 正在启动控制台: http://127.0.0.1:8890
python batch_console.py 8890
pause
