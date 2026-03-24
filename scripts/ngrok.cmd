@echo off
REM Always use ngrok 3.20+ from %LOCALAPPDATA%\Programs\Ngrok (see scripts/install-ngrok-global.ps1)
set "NGROK_EXE=%LOCALAPPDATA%\Programs\Ngrok\ngrok.exe"
if not exist "%NGROK_EXE%" (
  echo ERROR: %NGROK_EXE% not found. Run: powershell -ExecutionPolicy Bypass -File scripts/install-ngrok-global.ps1
  exit /b 1
)
"%NGROK_EXE%" %*
