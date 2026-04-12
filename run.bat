@echo off
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [Success] Running with Administrator privileges.
    python main_vision.py
) else (
    echo [ERROR] PLEASE RIGHT-CLICK AND "RUN AS ADMINISTRATOR"
    echo This is required for MIDI communication.
    pause
)