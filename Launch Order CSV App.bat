@echo off
title Order CSV Creator
echo ============================================
echo  Order CSV Creator - Startup
echo ============================================
echo.

echo [1/3] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python from python.org
    pause
    exit /b 1
)

echo.
echo [2/3] Installing required packages (streamlit, requests)...
pip install streamlit requests
if errorlevel 1 (
    echo ERROR: Failed to install packages.
    pause
    exit /b 1
)

echo.
echo [3/3] Launching app in your browser...
echo (Keep this window open while using the app. Close it to stop the app.)
echo.
streamlit run "%~dp0order_csv_app.py"

pause
