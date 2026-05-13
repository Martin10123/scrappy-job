# JobTrend AI

Proyecto MVP para recolectar ofertas de empleo tech en Colombia, procesar los datos y exponerlos a través de una API y un dashboard.

## Estructura del proyecto

- `app/`
  - `api/` -> rutas de FastAPI
  - `models/` -> modelos de datos SQLAlchemy
  - `repositories/` -> patrón Repository para acceso a datos
  - `schemas/` -> Pydantic schemas para validación
  - `services/` -> lógica de negocio
- `scrapers/` -> extracciones de fuentes de ofertas
- `ml/` -> NLP y clasificación
- `dashboard/` -> app de Streamlit
- `data/` -> volúmenes y datos locales

## Patrón de diseño

Usaremos el patrón `Repository` para separar:

- la lógica de acceso a datos (`app/repositories`)
- la lógica de negocio (`app/services`)

Esto mejora la mantenibilidad y facilita pruebas unitarias.

## Inicio rápido

### 1. Configurar entorno
```bash
# Crear venv
python -m venv venv
venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Levantar base de datos
```bash
docker-compose up -d
```

### 3. Verificar conexión
```bash
python test_db.py
```

### 4. Levantar API
```bash
uvicorn app.main:app --reload
```

Visita `http://127.0.0.1:8000/docs` para la documentación interactiva.

### 5. Ejecutar scraping
```bash
# Opción 1: Script manual
python run_scraping.py

# Opción 2: API
curl -X POST "http://127.0.0.1:8000/jobs/scrape/source/magneto365"

# Opción 3: Front-friendly endpoint
curl -X POST "http://127.0.0.1:8000/jobs/scrape/run" \
  -H "Content-Type: application/json" \
  -d "{\"source\":\"magneto365\",\"search_term\":\"desarrollador\",\"location\":\"colombia\",\"max_pages\":3}"

# Consultar progreso para loading en front
curl "http://127.0.0.1:8000/jobs/scrape/status/<task_id>"
```

Ejemplo de flujo para front:
1. Hacer POST a /jobs/scrape/run (o /jobs/scrape/source/{source}).
2. Leer task_id y status_url de la respuesta.
3. Hacer polling cada 2-3 segundos a status_url.
4. Renderizar progress_pct, current_source, processed_jobs/total_jobs y saved_jobs.
5. Detener polling cuando status sea completed o completed_with_errors.

### 6. Ver ofertas
```bash
curl "http://127.0.0.1:8000/jobs"
```

## Próximos pasos

1. **Ajustar scraper**: Inspeccionar HTML de Magneto365 y actualizar selectores en `scrapers/magneto/scraper.py`
2. **Añadir otra fuente**: Crear scraper similar para otra fuente (opcional)
3. **ETL Pipeline**: Limpiar y normalizar datos
4. **NLP Skills**: Extraer tecnologías de las descripciones
5. **Dashboard**: Crear visualización con Streamlit

## Deploy en Render (Docker + job cada 5 horas)

### 1. Subir repositorio a GitHub
Render despliega directamente desde un repositorio remoto.

### 2. Crear servicios con Blueprint
Este proyecto ya incluye `render.yaml` para crear:

- Un Web Service (`scrappy-job-api`) para la API FastAPI.
- Un Cron Job (`scrappy-job-scrape-every-5h`) para disparar scraping cada 5 horas.

En Render:

1. Ir a Dashboard -> New -> Blueprint.
2. Conectar el repositorio.
3. Confirmar creación de servicios del `render.yaml`.

### 3. Configurar variable obligatoria del cron
En el web service, configurar:

- `DATABASE_URL`: cadena de conexión PostgreSQL (Render Postgres, Neon, Supabase, etc.)

En el servicio de cron, configurar:

- `SCRAPE_API_URL`: URL base pública de tu API, por ejemplo `https://scrappy-job-api.onrender.com`

El cron ejecuta:

```bash
POST /jobs/scrape/run
```

con payload sin `source`, por lo que ejecuta todas las fuentes configuradas (`magneto365`, `getonboard`).

Ademas, el cron envia la lista completa de terminos de busqueda:

- desarrollador
- frontend
- backend
- python
- react
- fullstack
- Angular
- Laravel
- Programacion
- Desarrollador mobile
- DevOps
- Data Science
- IA

### 4. Verificar estado

1. Abrir logs del cron en Render y validar respuesta 200/202.
2. Revisar logs del web service para confirmar ejecución del scraping.
3. Consultar endpoint `/jobs` o analytics para validar nuevos registros.
