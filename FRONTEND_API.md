# API para Frontend - JobTrend AI

Base URL: http://127.0.0.1:8000

## 1) Listado simple
GET /jobs/

Retorna: arreglo de ofertas.

Campos por oferta:
- id
- source
- title
- company
- city
- remote_type
- salary_min
- salary_max
- currency
- description
- category
- seniority
- skills
- url
- published_at
- scraped_at

## 2) Búsqueda paginada
GET /jobs/search

Query params:
- source (opcional)
- city (opcional)
- remote_type (opcional)
- search (opcional, busca por title/company/description)
- limit (opcional, default 50, max 200)
- offset (opcional, default 0)

Retorna:
- total: total de registros que cumplen filtros
- limit
- offset
- items: arreglo de ofertas

## 3) Resumen de analítica
GET /jobs/analytics/overview

Query params:
- source (opcional)
- city (opcional)
- top_n (opcional, default 10)

Retorna:
- total_jobs
- top_sources
- top_cities
- remote_type_distribution
- seniority_distribution
- top_skills
- salary:
  - avg_salary_min
  - avg_salary_max
  - with_salary_min_count
  - with_salary_max_count
- monthly_trend

## 4) Forecast de demanda por skill
GET /jobs/analytics/forecast

Query params:
- source (opcional)
- city (opcional)
- top_n (opcional, default 10)
- months_ahead (opcional, default 3, max 12)

Retorna:
- generated_at
- horizon_months
- top_n
- total_jobs_analyzed
- skills: arreglo con
  - skill
  - history: [{month, count}]
  - forecast: [{month, count}]
  - total_observed
  - projected_total
  - growth_pct

## 5) Confianza del forecast
GET /jobs/analytics/forecast-confidence

Query params:
- source (opcional)
- city (opcional)
- top_n (opcional, default 10)
- test_horizon_months (opcional, default 2, max 6)

Retorna:
- generated_at
- top_n
- test_horizon_months
- total_jobs_analyzed
- skills: arreglo con
  - skill
  - train_points
  - test_points
  - mae
  - mape_pct
  - confidence_level (high | medium | low | insufficient-data)

## Ejemplos rápidos
- /jobs/search?search=python&city=bogota&limit=20&offset=0
- /jobs/analytics/overview?top_n=8
- /jobs/analytics/forecast?top_n=8&months_ahead=6
- /jobs/analytics/forecast-confidence?top_n=8&test_horizon_months=3
