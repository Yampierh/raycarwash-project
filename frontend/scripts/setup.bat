@echo off
REM Frontend Setup Script for Windows
REM Run this script to install dependencies

echo ========================================
echo RayCarwash Frontend Setup
echo ========================================

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
cd .. 
call npm install

REM Copy .env.example to .env.local if it doesn't exist
if not exist ".env.local" (
    echo Creating .env.local from .env.example...
    copy ..\.env.example .env.local
    echo IMPORTANT: Please edit .env.local with your configuration
)

echo ========================================
echo Setup complete!
echo ========================================
echo.
echo To start the frontend, run:
echo   npm start
echo.
