@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0create-shortcut.ps1"
if errorlevel 1 (
  echo.
  echo Could not create the shortcut. See the message above.
  pause
  exit /b 1
)
echo.
pause
exit /b 0
