# JobTrend AI — MVP en Python

## Objetivo del MVP
Construir una primera versión funcional de **JobTrend AI** que recopile ofertas laborales tech en Colombia, procese datos automáticamente y muestre tendencias del mercado en un dashboard.

---

# Alcance del MVP (90 días)

## Funcionalidades principales

### 1. Web Scraping Inicial
Fuentes prioritarias:
- Magneto365
n- Computrabajo
- Elempleo (opcional fase 2)

Funciones:
- Extraer título del empleo
- Empresa
- Ciudad
- Modalidad (remoto/presencial/híbrido)
- Salario (si existe)
- Descripción
- Fecha publicación
- URL
- Fuente

### 2. Limpieza y Normalización
Pipeline en Python que:
- Elimina duplicados
- Estandariza ciudades
- Limpia texto HTML
- Convierte salarios a COP
- Detecta rangos salariales
- Normaliza nombres de tecnologías

### 3. Extracción de Skills (NLP)
Detectar tecnologías dentro de la descripción:
- Python
n- JavaScript
- React
- Vue
- Node.js
- Docker
- AWS
- PostgreSQL
- Kubernetes
- etc.

Salida:
```json
{
  "skills": ["python", "django", "docker"]
}
```

### 4. Clasificación Automática del Cargo
Modelo inicial por reglas + ML simple:
- Backend
- Frontend
- Data
- DevOps
- Mobile
- QA

### 5. Clasificación de Seniority
Detectar:
- Junior
- Mid
- Senior

Basado en:
- Palabras clave
- Años de experiencia
- Salario estimado

### 6. API REST con FastAPI
Endpoints MVP:

```bash
GET /jobs
GET /jobs/{id}
GET /stats/top-skills
GET /stats/salaries
GET /stats/categories
GET /stats/cities
GET /stats/seniority
```

### 7. Dashboard MVP
Con Streamlit o Metabase:
- Top skills más pedidas
- Salarios por rol
- Vacantes por ciudad
- Distribución seniority
- Tendencias semanales
- Empresas que más contratan

---

# Stack Tecnológico MVP

## Backend
- Python 3.11+
- FastAPI
- Uvicorn

## Scraping
- Scrapy
- Playwright (solo si una fuente lo requiere)
- BeautifulSoup (soporte auxiliar)

## Datos
- PostgreSQL (recomendado MVP)
- SQLAlchemy
- Alembic

## Data / ML
- Pandas
- scikit-learn
- spaCy

## Visualización
- Streamlit (rápido para MVP)

## Infraestructura
- Docker
- Docker Compose

---

# Arquitectura MVP

```text
Scrapers -> ETL -> PostgreSQL -> FastAPI -> Dashboard
                 -> ML/NLP
```

---

# Estructura del Proyecto

```bash
jobtrend-ai/
│── app/
│   ├── api/
│   ├── models/
│   ├── services/
│   └── main.py
│
│── scrapers/
│   ├── magneto/
│   ├── computrabajo/
│   └── base/
│
│── ml/
│   ├── classify_category.py
│   ├── seniority.py
│   └── skill_extractor.py
│
│── dashboard/
│   └── streamlit_app.py
│
│── data/
│── docker-compose.yml
│── requirements.txt
│── README.md
```

---

# Base de Datos MVP (PostgreSQL)

## Tabla jobs

```sql
id
source
title
company
city
remote_type
salary_min
salary_max
currency
description
category
seniority
skills(json)
url
published_at
scraped_at
```

---

# Roadmap por Fases

## Semana 1-2
- Configuración proyecto
- Docker
- PostgreSQL
- FastAPI base

## Semana 3-4
- Scraper Magneto365
- Scraper Computrabajo
- Guardado en BD

## Semana 5-6
- Limpieza ETL
- Skills extractor
- Normalización salarios

## Semana 7-8
- Clasificación categoría
- Clasificación seniority

## Semana 9-10
- API REST completa
- Filtros y paginación

## Semana 11-12
- Dashboard Streamlit
- Deploy demo

---

# KPIs del MVP

- 1000+ ofertas recolectadas
- Actualización diaria automática
- 85% precisión clasificación categoría
- 80% detección seniority
- Dashboard funcional en tiempo real

---

# Futuras Mejoras

- Alertas por email de nuevas vacantes
- Predicción salarial con ML
- Ranking de skills emergentes
- CV matcher con ofertas
- Recomendador de carrera tech
- Multi país LATAM
- SaaS freemium

---

# Recomendación Técnica Realista

Para el MVP usa:
- **PostgreSQL solamente** (no Mongo todavía)
- **Streamlit en vez de Metabase**
- **Reglas + ML simple** primero
- **2 fuentes laborales iniciales**
- **Deploy en Render / Railway / VPS**

---

# Resultado Esperado MVP

Una plataforma web que muestre:
- Qué tecnologías están contratando en Colombia
- Cuánto pagan por rol
- Qué ciudades tienen más demanda
- Qué nivel buscan las empresas
- Tendencias del mercado tech

