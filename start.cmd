@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
set "CODERECALL_EXIT=%ERRORLEVEL%"
if not "%CODERECALL_EXIT%"=="0" (
    echo.
    echo Startup failed. Read the message above, then press any key to close.
    pause >nul
)
exit /b %CODERECALL_EXIT%
