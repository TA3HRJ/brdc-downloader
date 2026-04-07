@echo off
:: Launches the BRDC Downloader GUI (no console window)
cd /d "%~dp0"
pythonw brdc_downloader.py
if errorlevel 1 (
    echo Python not found or error occurred. >> brdc_error.log
    echo Solution: install Python from https://www.python.org >> brdc_error.log
    pause
)
