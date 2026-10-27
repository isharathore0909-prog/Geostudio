@echo off
set "PATH=%LOCALAPPDATA%\Microsoft\dotnet;%ProgramFiles%\dotnet;%PATH%"
taskkill /F /IM GeoStudio.exe >nul 2>&1
echo Building and Launching GeoStudio...
cd /d "%~dp0GeoStudio"
dotnet build -c Debug
if %ERRORLEVEL% equ 0 (
    echo Starting GeoStudio...
    start "" "bin\Debug\net8.0-windows\GeoStudio.exe"
    timeout /t 2 /nobreak >nul
) else (
    echo [ERROR] Build failed! Check compiler output above.
    pause
)
