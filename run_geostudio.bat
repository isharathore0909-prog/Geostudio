@echo off
set "PATH=%LOCALAPPDATA%\Microsoft\dotnet;%PATH%"
set "DOTNET_ROOT=%LOCALAPPDATA%\Microsoft\dotnet"
taskkill /F /IM GeoStudio.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul
echo Launching GeoStudio v1.0.0 — Standalone GIS...
cd /d "%~dp0GeoStudio"
dotnet run
