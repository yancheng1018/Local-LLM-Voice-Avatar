@echo off
cd /d "%~dp0"
if not exist "runtime\python.exe" (
    echo ERROR: runtime\python.exe not found.
    pause
    exit /b 1
)
if not exist "start_v4_dpo.py" (
    echo ERROR: start_v4_dpo.py not found.
    pause
    exit /b 1
)
"runtime\python.exe" "%~dp0start_v4_dpo.py"
pause
