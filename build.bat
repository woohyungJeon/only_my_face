@echo off
rem Double-click this file to build dist\OnlyMyFace-Setup.exe
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_release.ps1"
echo.
pause
