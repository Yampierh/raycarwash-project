@echo off
REM Backend Setup Script for Windows
REM Run this script to install dependencies and set up the environment

echo ========================================
echo RayCarwash Backend Setup
echo ========================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Copy .env.example to .env if it doesn't exist
if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo IMPORTANT: Please edit .env with your configuration
)

echo ========================================
echo Setup complete!
echo ========================================
echo.
echo To start the backend, run:
echo   scripts\start.bat
echo.
echo To activate the environment manually:
echo   venv\Scripts\activate.bat
echo.
