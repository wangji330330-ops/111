@echo off
chcp 65001 >nul
title 中药学复习系统 · 网页版（本地服务器）
cd /d "%~dp0"

echo ============================================================
echo   中药学复习系统 · 网页版
echo   正在启动本地服务器，请勿关闭本窗口
echo ============================================================
echo.

rem 找 Python
set PY=
where python >nul 2>nul && set PY=python
if "%PY%"=="" (
  if exist "%LOCALAPPDATA%\Programs\Python" (
    for /f "delims=" %%i in ('dir /b /s "%LOCALAPPDATA%\Programs\Python\python.exe" 2^>nul') do set PY=%%i
  )
)
if "%PY%"=="" (
  if exist "C:\Python312\python.exe" set PY=C:\Python312\python.exe
  if exist "C:\Python311\python.exe" set PY=C:\Python311\python.exe
)

if "%PY%"=="" (
  echo [!] 没有找到 Python。
  echo     请改用「docs\离线版.html」直接双击打开，功能完全一样。
  echo.
  pause
  exit /b 1
)

echo 本机访问：  http://127.0.0.1:8080/
echo 局域网访问：请用手机连同一个 WiFi，打开下面显示的 192.168.x.x 地址
echo.
echo （关闭本窗口即停止服务器）
echo.

start "" http://127.0.0.1:8080/
"%PY%" -m http.server 8080 --directory docs
pause
