@echo off
chcp 65001 > nul
echo ========================================
echo   JobTrend AI - Ejecutar Proyecto
echo ========================================
echo.

echo.
echo ✅ Iniciando API FastAPI...
echo 📍 URL local: http://localhost:9000
echo 📍 Documentación: http://localhost:9000/docs
echo 📍 CORS Configurado para: http://localhost:5173
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

REM Ejecutar la API
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

pause
