@echo off
setlocal
cd /d "%~dp0"

rem ============================================================
rem  Local-LLM-Voice-Avatar 启动器
rem
rem  双击即可运行（不显示控制台窗口）。
rem  若需要查看报错信息，在命令行执行：  启动器.bat debug
rem ============================================================

set "ROOT=%~dp0"
set "PY=%ROOT%.venv-gui\Scripts\python.exe"
set "PYW=%ROOT%.venv-gui\Scripts\pythonw.exe"
set "APP=%ROOT%launcher\OpenLLMVTuber_GUI.py"

if not exist "%APP%" (
    echo.
    echo [错误] 找不到启动器脚本：
    echo     %APP%
    echo.
    echo 请确认本文件位于 Local-LLM-Voice-Avatar 项目根目录。
    echo.
    pause
    exit /b 1
)

if not exist "%PY%" (
    echo.
    echo [错误] 找不到 GUI 虚拟环境 .venv-gui
    echo     %ROOT%.venv-gui
    echo.
    echo 请先在项目根目录执行以下命令创建环境并安装依赖：
    echo.
    echo     uv venv .venv-gui --seed
    echo     .venv-gui\Scripts\python.exe -m pip install PySide6-Essentials ruamel.yaml psutil
    echo.
    pause
    exit /b 1
)

if /i "%~1"=="debug" (
    echo [启动器] 调试模式：关闭此窗口即退出程序
    echo.
    "%PY%" "%APP%"
    echo.
    echo [启动器] 程序已退出，错误码 %ERRORLEVEL%
    pause
) else (
    start "" "%PYW%" "%APP%"
)

exit /b 0
