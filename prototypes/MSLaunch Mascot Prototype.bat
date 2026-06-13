@echo off
setlocal
cd /d "%~dp0"
where pyw >nul 2>nul
if not errorlevel 1 (
    start "" pyw -3 "%~dp0mslaunch_mascot_prototype.py"
    exit /b 0
)
where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw "%~dp0mslaunch_mascot_prototype.py"
    exit /b 0
)
start "" py -3 "%~dp0mslaunch_mascot_prototype.py"
