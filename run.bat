@echo off
setlocal enabledelayedexpansion
title FL Gesture Controller - Launcher (BETA)

:: Generate the Escape character for colors
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
set "PINK=%ESC%[38;2;222;29;93m"
set "RESET=%ESC%[0m"
set "GRAY=%ESC%[90m"
set "RED=%ESC%[91m"

:: ADMINISTRATOR CHECK
net session >nul 2>&1
if not %errorLevel% == 0 (
    echo %RED%====================================================
    echo    ERROR: ADMINISTRATOR PRIVILEGES REQUIRED
    echo ====================================================%RESET%
    echo %GRAY%Please right-click 'run.bat' and select 'Run as Administrator'.%RESET%
    echo This is necessary for loopMIDI communication.
    echo.
    pause
    exit /b
)

:menu
cls
echo %PINK%====================================================
echo    FL GESTURE CONTROLLER - BROWSER SELECTION
echo ====================================================%RESET%
echo.
echo %GRAY%Select your preferred browser for the UI:%RESET%
echo %PINK%[1]%RESET% Chrome
echo %PINK%[2]%RESET% Opera (GX)
echo %PINK%[3]%RESET% Firefox
echo %PINK%[4]%RESET% Edge
echo %PINK%[Q]%RESET% QUIT
echo.

set "choice="
set "b_key="
set "exe_name="

set /p choice="Enter number (1-4/Q): "

:: [1] Handle Quit
if /i "%choice%"=="Q" exit /b

:: [2] Map choices and identify EXE names for checking
if "%choice%"=="1" (set "b_key=chrome" & set "exe_name=chrome.exe")
if "%choice%"=="2" (set "b_key=opera" & set "exe_name=opera.exe")
if "%choice%"=="3" (set "b_key=firefox" & set "exe_name=firefox.exe")
if "%choice%"=="4" (set "b_key=edge" & set "exe_name=msedge.exe")

:: [3] VALIDATION: Check if key is defined
if not defined b_key (
    echo.
    echo %RED%Invalid option "%choice%". Please try again.%RESET%
    timeout /t 2 >nul
    goto menu
)

:: [4] INSTALLATION CHECK: Use 'where' to see if browser exists
where %exe_name% >nul 2>&1
if not %errorLevel% == 0 (
    echo.
    echo %RED%Error: %exe_name% not found on this system.%RESET%
    echo %GRAY%Please choose a browser that is installed.%RESET%
    timeout /t 3 >nul
    goto menu
)

:: Save choice to temp file in the project directory
echo %b_key% > "%~dp0.browser_cfg"

echo.
echo %PINK%~SUCCESS~%RESET% Starting application in %PINK%!b_key!%RESET%
echo %GRAY%================================================================================%RESET%
echo %RED%[Please keep this window open. This app will not run if this window is closed.]%RESET%
echo %GRAY%================================================================================%RESET%
echo.

:: Run Python using the absolute path of the script's folder
python "%~dp0main_vision.py"

if not %errorLevel% == 0 (
    echo.
    echo %RED%[Error] The application crashed or failed to start.%RESET%
    echo %GRAY%Check if Python is installed and added to your PATH.%RESET%
)
pause