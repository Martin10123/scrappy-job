# JobTrend AI — MVP con Playwright

> Plataforma de tendencias del mercado tech en Colombia

---

## 1. Objetivo del MVP

Construir una primera versión funcional de **JobTrend AI** que recopile ofertas laborales tech en Colombia usando **Playwright como único motor de scraping**, procese los datos automáticamente y muestre tendencias del mercado en un dashboard.

> **¿Por qué solo Playwright?**
> Playwright maneja JavaScript pesado, auto-espera a que los elementos estén listos, soporta múltiples navegadores desde una sola API y permite interceptar peticiones de red. Es suficiente para todas las fuentes del MVP sin necesidad de Scrapy.

---

## 2. Alcance del MVP (90 días)

### 2.1 Fuentes de scraping

- **Magneto365** — portal con React, requiere esperar hidratación del cliente
- **Computrabajo** — listados con paginación infinita (scroll)
- **Elempleo** — fase 2 opcional

### 2.2 Datos a extraer por oferta

| Campo | Descripción |
|---|---|
| `title` | Título del cargo |
| `company` | Nombre de la empresa |
| `city` | Ciudad normalizada |
| `remote_type` | remoto / presencial / híbrido |
| `salary_min / max` | En COP, null si no se publica |
| `description` | HTML limpio → texto plano |
| `skills` | JSON: `["python", "docker"]` |
| `category` | Backend / Frontend / Data / DevOps... |
| `seniority` | Junior / Mid / Senior |
| `url` | URL canónica (unique) |
| `published_at` | Fecha de publicación |
| `scraped_at` | Timestamp del scraping |
| `source` | magneto / computrabajo |
| `is_active` | True mientras la oferta exista |

---

## 3. Arquitectura del sistema

```
Playwright Scrapers
       ↓
  ETL Pipeline (limpieza + NLP)
       ↓
  PostgreSQL
       ↓
  FastAPI  →  Dashboard Streamlit
```

### 3.1 Estructura del proyecto

```
jobtrend-ai/
├── scrapers/
│   ├── base/
│   │   ├── browser.py          # factory del contexto Playwright
│   │   └── base_scraper.py     # clase abstracta
│   ├── magneto/
│   │   └── magneto_scraper.py
│   └── computrabajo/
│       └── computrabajo_scraper.py
├── etl/
│   ├── cleaner.py              # HTML → texto, normalizar ciudades
│   ├── salary_parser.py        # parsear rangos en texto libre
│   └── deduplicator.py         # por URL + hash título+empresa
├── ml/
│   ├── skill_extractor.py      # spaCy PhraseMatcher
│   ├── classify_category.py    # reglas + LogisticRegression
│   └── seniority.py
├── app/
│   ├── api/                    # FastAPI endpoints
│   └── models/                 # SQLAlchemy
├── dashboard/
│   └── streamlit_app.py
├── docker-compose.yml
└── requirements.txt
```

---

## 4. Módulo de scraping con Playwright

### 4.1 Factory del browser

El factory centraliza la configuración anti-detección: stealth mode, user-agent real, viewport e interceptación de recursos innecesarios.

```python
# scrapers/base/browser.py
from playwright.async_api import async_playwright, BrowserContext
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
]

async def get_context(playwright) -> BrowserContext:
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": 1920, "height": 1080},
        locale="es-CO",
    )
    # Bloquear imágenes y fuentes para ahorrar ancho de banda
    await context.route(
        "**/*",
        lambda r: r.abort() if r.request.resource_type in
            ["image", "font", "media"] else r.continue_()
    )
    return context
```

### 4.2 Clase base del scraper

```python
# scrapers/base/base_scraper.py
from abc import ABC, abstractmethod
from playwright.async_api import Page
from tenacity import retry, stop_after_attempt, wait_exponential

class BaseScraper(ABC):
    SOURCE: str = ""

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_page(self, page: Page, url: str):
        await page.goto(url, wait_until="networkidle", timeout=30_000)

    @abstractmethod
    async def scrape_listings(self, page: Page) -> list[dict]:
        """Retorna lista de ofertas crudas."""

    @abstractmethod
    async def scrape_detail(self, page: Page, url: str) -> dict:
        """Extrae el detalle completo de una oferta."""
```

### 4.3 Scraper de Magneto365

Magneto usa React con hidratación del lado del cliente. La clave es esperar al selector correcto antes de extraer datos, y manejar la paginación via parámetros de URL.

```python
# scrapers/magneto/magneto_scraper.py
import asyncio, random
from playwright.async_api import Page
from scrapers.base.base_scraper import BaseScraper

BASE_URL = "https://www.magneto365.com/es/empleos?q=tech"

class MagnetoScraper(BaseScraper):
    SOURCE = "magneto"

    async def scrape_listings(self, page: Page) -> list[dict]:
        jobs = []
        for pg in range(1, 6):   # primeras 5 páginas
            url = f"{BASE_URL}&page={pg}"
            await self.fetch_page(page, url)

            # Esperar que React hidrate los cards
            await page.wait_for_selector('[data-testid="job-card"]',
                                         timeout=15_000)

            cards = await page.query_selector_all('[data-testid="job-card"]')
            for card in cards:
                title   = await card.query_selector('[data-testid="job-title"]')
                company = await card.query_selector('[data-testid="company-name"]')
                link    = await card.query_selector('a')
                jobs.append({
                    "title":   await title.inner_text()          if title   else "",
                    "company": await company.inner_text()        if company else "",
                    "url":     await link.get_attribute('href')  if link    else "",
                    "source":  self.SOURCE,
                })

            await asyncio.sleep(random.uniform(1.5, 3.0))  # delay humano
        return jobs
```

### 4.4 Anti-detección — reglas clave

| Técnica | Implementación |
|---|---|
| Stealth mode | `playwright-stealth` oculta `navigator.webdriver` |
| Delays aleatorios | `random.uniform(1.5, 3.0)` entre acciones |
| Rotar user-agent | Lista de UAs reales, uno por sesión |
| Bloquear recursos | Abortar imágenes, fuentes y media via `route()` |
| Máx. 50 req/hora | Rate limiting en el orquestador principal |
| Screenshot en error | `page.screenshot()` al capturar excepciones |

---

## 5. Pipeline ETL

### 5.1 Limpieza y normalización

- Eliminar etiquetas HTML con BeautifulSoup (auxiliar, no scraper)
- Estandarizar ciudades: `"Bogotá D.C."` → `"Bogotá"`
- Convertir salarios en texto libre a rango COP con regex
- Deduplicar por URL única y hash de título+empresa

### 5.2 Parser de salarios

Es uno de los módulos más críticos. Las ofertas en Colombia usan formatos muy variados:

```python
# etl/salary_parser.py
import re

PATTERNS = [
    r'\$(\d[\d.,]+)\s*[-a]\s*\$(\d[\d.,]+)',   # $3.000.000 a $5.000.000
    r'(\d+)\s*(?:millones?|mlls?)',              # 3 millones
    r'(\d+)\s*SMMLV',                           # 2 SMMLV
]

SMMLV_2025 = 1_423_500

def parse_salary(text: str) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    # ... lógica de parseo por patrón
    return salary_min, salary_max
```

---

## 6. Extracción de skills con spaCy

Se usa `PhraseMatcher` con aliases normalizados para cubrir variantes como `node`, `nodejs`, `node.js`, `Node.JS`:

```python
# ml/skill_extractor.py
import spacy
from spacy.matcher import PhraseMatcher

SKILLS_ALIASES = {
    "python":  ["python", "Python", "Python3"],
    "nodejs":  ["node", "nodejs", "node.js", "Node.JS"],
    "docker":  ["docker", "Docker", "Docker Engine"],
    "react":   ["react", "React", "ReactJS", "React.js"],
    # ... +50 tecnologías
}

nlp = spacy.blank("es")
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

for skill, aliases in SKILLS_ALIASES.items():
    patterns = [nlp.make_doc(a) for a in aliases]
    matcher.add(skill, patterns)

def extract_skills(text: str) -> list[str]:
    doc = nlp(text)
    matches = matcher(doc)
    return list({nlp.vocab.strings[match_id] for match_id, _, _ in matches})
```

---

## 7. API REST con FastAPI

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/jobs` | Listado con filtros y paginación |
| GET | `/jobs/{id}` | Detalle de una oferta |
| GET | `/stats/top-skills` | Skills más pedidas |
| GET | `/stats/salaries` | Salarios por rol y seniority |
| GET | `/stats/cities` | Vacantes por ciudad |
| GET | `/stats/seniority` | Distribución de seniority |
| GET | `/stats/categories` | Vacantes por categoría |

---

## 8. Stack tecnológico

| Capa | Tecnología | Rol |
|---|---|---|
| Scraping | Playwright (async) | Motor único de scraping |
| Scraping | playwright-stealth | Anti-detección |
| Scraping | tenacity | Reintentos automáticos |
| ETL | BeautifulSoup + pandas | Limpieza y normalización |
| NLP / ML | spaCy + scikit-learn | Skills y clasificación |
| BD | PostgreSQL + SQLAlchemy | Almacenamiento principal |
| BD | Alembic | Migraciones |
| API | FastAPI + Uvicorn | Servicio REST |
| Dashboard | Streamlit + Plotly | Visualización MVP |
| Infra | Docker + Docker Compose | Orquestación local |
| Scheduler | APScheduler | Cron diario a las 6am |

---

## 9. Esquema PostgreSQL

```sql
CREATE TABLE jobs (
    id           SERIAL PRIMARY KEY,
    source       VARCHAR(30)  NOT NULL,
    title        TEXT         NOT NULL,
    company      TEXT,
    city         VARCHAR(80),
    remote_type  VARCHAR(20),   -- remoto | presencial | híbrido
    salary_min   INTEGER,       -- COP, null si no publicado
    salary_max   INTEGER,
    currency     VARCHAR(5) DEFAULT 'COP',
    description  TEXT,
    category     VARCHAR(30),   -- Backend | Frontend | Data...
    seniority    VARCHAR(10),   -- Junior | Mid | Senior
    skills       JSONB,         -- ["python", "docker"]
    url          TEXT UNIQUE NOT NULL,
    is_active    BOOLEAN DEFAULT TRUE,
    published_at TIMESTAMP,
    scraped_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_jobs_category  ON jobs(category);
CREATE INDEX idx_jobs_city      ON jobs(city);
CREATE INDEX idx_jobs_seniority ON jobs(seniority);
CREATE INDEX idx_jobs_skills    ON jobs USING GIN(skills);
```

---

## 10. Roadmap 90 días

| Semanas | Fase | Entregables |
|---|---|---|
| 1 – 2 | Base | Docker Compose, PostgreSQL, FastAPI skeleton, Playwright instalado |
| 3 – 4 | Scrapers | Scraper Magneto365 + Computrabajo, guardado en BD |
| 5 – 6 | ETL | Limpieza HTML, normalizar ciudades, salary parser |
| 7 – 8 | NLP / ML | Skill extractor, clasificación categoría y seniority |
| 9 – 10 | API + Deploy | Endpoints completos, deploy en Railway/Render (staging) |
| 11 – 12 | Dashboard | Streamlit completo, tendencias semanales, demo pública |

---

## 11. KPIs del MVP

- 1 000+ ofertas recolectadas en el primer run
- Actualización diaria automática a las 6am
- 85% precisión en clasificación de categoría
- 80% precisión en detección de seniority
- Dashboard funcional con datos del día anterior

---

## 12. Riesgos y mitigaciones

| Riesgo | Prob. | Mitigación |
|---|---|---|
| Portales cambian su HTML | Alta | Selectores en config YAML, tests de selectores en CI |
| Salarios no publicados (>60%) | Alta | Campo nullable desde el inicio, modelo estimación fase 2 |
| Bloqueo de IP | Media | Delays + rate limiting + playwright-stealth |
| 90 días insuficientes | Media | Priorizar scraping + dashboard; API puede simplificarse |
| Precisión NLP < objetivo | Media | Reglas primero, ML solo si precisión < 70% |

---

## 13. Mejoras futuras (post-MVP)

- Alertas por email / Telegram de nuevas vacantes
- Predicción salarial con ML
- Ranking de skills emergentes semana a semana
- CV matcher con ofertas
- Expansión a México, Argentina y Chile
- SaaS freemium con plan premium para empresas
