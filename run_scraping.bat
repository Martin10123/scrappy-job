@echo off
chcp 65001 > nul
echo ========================================
echo   JobTrend AI - Ejecutar Scraping
echo ========================================
echo.

echo.
echo ✅ Iniciando proceso de Scraping...
echo.

REM Ejecutar el scraping
python run_scraping.py

pause
