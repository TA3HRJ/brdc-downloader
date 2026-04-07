@echo off
:: Konsol penceresi hemen kapanır, GUI açılır
cd /d "%~dp0"
pythonw brdc_downloader.py
if errorlevel 1 (
    echo Python bulunamadi veya hata olustu. >> brdc_error.log
    echo Cozum: https://www.python.org adresinden Python yukleyin. >> brdc_error.log
    pause
)
