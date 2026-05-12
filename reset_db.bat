@echo off
setlocal
chcp 65001 > nul

echo ========================================
echo   JobTrend AI - Reset de Base de Datos
echo ========================================
echo.
echo Esto va a borrar todos los datos locales de PostgreSQL y recrear la base desde cero.
echo.
set /p CONFIRM=Escribe BORRAR para continuar: 
if /I not "%CONFIRM%"=="BORRAR" (
    echo Operacion cancelada.
    pause
    exit /b 1
)
echo.
echo Deteniendo contenedores...
docker-compose down
if errorlevel 1 (
    echo No se pudo detener docker-compose.
    pause
    exit /b 1
)

echo.
echo Borrando data/postgres...
if exist "data\postgres" (
    rmdir /s /q "data\postgres"
)
mkdir "data\postgres"

echo.
echo Levantando PostgreSQL limpio...
docker-compose up -d db
if errorlevel 1 (
    echo No se pudo levantar la base de datos.
    pause
    exit /b 1
)

echo.
echo Esperando unos segundos para que PostgreSQL termine de iniciar...
timeout /t 8 /nobreak > nul

echo.
echo Base de datos reiniciada.
echo Al arrancar la API, las tablas se recrearan automaticamente.
echo.
pause
