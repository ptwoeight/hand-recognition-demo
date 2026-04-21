@echo off
setlocal enabledelayedexpansion
title FL Gesture Controller - Installer (BETA)

:: makes the esc char for colours
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"

:: define colours
set "PINK=%ESC%[38;2;222;29;93m"
set "RESET=%ESC%[0m"
set "GRAY=%ESC%[90m"

cls
echo %PINK%====================================================
echo    FL GESTURE CONTROLLER - SYSTEM INSTALLER
echo ====================================================%RESET%
echo.

:: --- loading bar
echo %GRAY%[Checking System Requirements...]%RESET%
set "bar=####################"
for /L %%i in (1,1,20) do (
    set /p "=%PINK%#%RESET%" <nul
    timeout /t 0 /nobreak >nul
)
echo %PINK% [OK]%RESET%

echo.
echo %PINK%Installing Python dependencies...%RESET%
echo %GRAY%----------------------------------------------------%RESET%
pip install -r requirements.txt
echo %GRAY%----------------------------------------------------%RESET%

echo.
echo %PINK%~ INSTALLATION COMPLETE ~%RESET%
echo.
echo %GRAY%Click 'run.bat' to run app! %RESET%
echo %GRAY%(Right click and 'Run as Administrator')%RESET%
echo.
echo %PINK%~ HAPPY RECORDING ~ %RESET%
echo.
pause