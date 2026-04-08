@echo off
REM Backend Start Script for Windows
REM Run this script to start the development server

echo ========================================
echo Starting RayCarwash Backend
echo ========================================

REM Check if virtual environment exists
if not exist "venv" (
    echo ERROR: Virtual environment not found
    echo Run setup.bat first to create the environment
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo WARNING: .env file not found
    echo Using default configuration
    echo Run setup.bat to create a proper .env file
)

REM Start the server
echo Starting server at http://localhost:8000
uvicorn main:app --reload --host 0.0.0.0 --port 8000

