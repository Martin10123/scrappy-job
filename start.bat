@echo off
setlocal enabledelayedexpansion

echo ====================================
echo  INICIANDO JOBTREND AI PROJECT
echo ====================================
echo.

REM Obtener la ruta del proyecto
set PROJECT_DIR=%~dp0

REM Cambiar a la carpeta del proyecto
cd /d "%PROJECT_DIR%"

REM Crear venv si no existe
echo [1/4] Verificando entorno virtual...
if not exist "venv" (
    echo   Creando venv...
    python -m venv venv
)

REM Activar venv
call venv\Scripts\activate.bat

REM Detener y eliminar contenedores anteriores si existen
echo [2/4] Limpiando contenedores anteriores...
docker-compose down --remove-orphans 2>nul

REM Esperar un momento para liberar puertos
timeout /t 2 /nobreak

REM Levantar servicios de Docker (PostgreSQL y pgAdmin)
echo [2/4] Iniciando servicios de Docker...
docker-compose up -d

REM Esperar a que la BD esté lista
echo [3/4] Esperando a que PostgreSQL esté listo...
timeout /t 5 /nobreak

REM Instalar dependencias si es necesario
echo [4/4] Verificando dependencias Python...
pip install -r requirements.txt --quiet

REM Ejecutar el servidor FastAPI
echo.
echo ====================================
echo  🚀 Iniciando servidor en http://localhost:8000
echo  📊 pgAdmin disponible en http://localhost:8080
echo ====================================
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

REM Si el servidor se detiene, pausa para ver el error
pause
