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
curl -X POST "http://127.0.0.1:8000/jobs/scrape/magneto365"

# Opción 3: Front-friendly endpoint
curl -X POST "http://127.0.0.1:8000/jobs/scrape/run" \
  -H "Content-Type: application/json" \
  -d "{\"source\":\"magneto365\",\"search_term\":\"desarrollador\",\"location\":\"colombia\",\"max_pages\":3}"
```

### 6. Ver ofertas
```bash
curl "http://127.0.0.1:8000/jobs"
```

## Próximos pasos

1. **Ajustar scraper**: Inspeccionar HTML de Magneto365 y actualizar selectores en `scrapers/magneto/scraper.py`
2. **Añadir Computrabajo**: Crear scraper similar para otra fuente
3. **ETL Pipeline**: Limpiar y normalizar datos
4. **NLP Skills**: Extraer tecnologías de las descripciones
5. **Dashboard**: Crear visualización con Streamlit
