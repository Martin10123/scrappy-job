from typing import List, Union
from datetime import datetime

from app.logger import logger
from app.models.job import Job
from app.repositories.job_repository import JobRepository
from app.services.job_normalizer import normalize_skills
from scrapers.computrabajo.scraper import ComputrabajoScraper
from scrapers.magneto.scraper import MagnetoScraper
from scrapers.getonboard.scraper import run_getonboard_scraper

class ScrapingService:
    """Servicio para manejar el scraping y guardado de ofertas"""

    def __init__(self, repository: JobRepository):
        self.repository = repository
        self.scrapers = {
            'magneto365': MagnetoScraper(),
            'computrabajo': ComputrabajoScraper(),
            'getonboard': None,  # GetOnBoard usa async, se llama diferente
        }

    def scrape_and_save_jobs(self, source: str, search_term: Union[str, List[str]] = "desarrollador",
                           location: str = "colombia", max_pages: int = 5) -> int:
        """
        Scrape ofertas y las guarda en la base de datos

        Args:
            source: Fuente del scraper ('magneto365', 'computrabajo', 'getonboard')
            search_term: Término(s) de búsqueda (str o list)
            location: Ubicación (solo para magneto365/computrabajo)
            max_pages: Número máximo de páginas a scrapear

        Returns:
            Número de ofertas guardadas
        """
        if source not in self.scrapers:
            logger.error(f"Scraper no encontrado para source: {source}")
            raise ValueError(f"Scraper no encontrado para source: {source}")

        logger.info(f"Ejecutando scraper {source} para term='{search_term}' max_pages={max_pages}")

        # Obtener ofertas del scraper
        if source == 'getonboard':
            # GetOnBoard usa async
            if isinstance(search_term, str):
                search_term = [search_term]
            raw_jobs = run_getonboard_scraper(search_terms=search_term, max_pages=max_pages)
        else:
            # Magneto365 y ComputraBajo usan sync
            scraper = self.scrapers[source]
            raw_jobs = scraper.get_jobs(search_term=search_term, location=location, max_pages=max_pages)

        saved_count = 0
        processed_count = 0

        for raw_job in raw_jobs:
            processed_count += 1
            job_title = raw_job.get('title', 'Sin título')
            try:
                logger.info(f"[{processed_count}/{len(raw_jobs)}] Procesando: {job_title}")
                job_url = raw_job.get('url', '')
                
                # Verificar si ya existe (por URL)
                existing = self.repository.get_by_url(job_url)
                if existing:
                    logger.info(f"  ↳ Ya existe en BD. Intentando enriquecer...")
                    updated = self._merge_missing_fields(existing, raw_job)
                    if updated:
                        self.repository.update(existing)
                        logger.info(f"  ↳ ✅ Oferta enriquecida: {existing.title}")
                        saved_count += 1
                    else:
                        logger.info(f"  ↳ ℹ️ Sin cambios (todos los campos completos)")
                    continue

                # Crear objeto Job
                logger.info(f"  ↳ Es nueva. Guardando en BD...")
                job = Job(
                    source=raw_job.get('source'),
                    title=raw_job.get('title'),
                    company=raw_job.get('company'),
                    city=raw_job.get('city'),
                    location_text=raw_job.get('location_text'),
                    contract_type=raw_job.get('contract_type', raw_job.get('remote_type')),
                    work_mode=raw_job.get('work_mode'),
                    english_required=raw_job.get('english_required'),
                    salary_min=raw_job.get('salary_min'),
                    salary_max=raw_job.get('salary_max'),
                    currency=raw_job.get('currency'),
                    description=raw_job.get('description'),
                    skills=normalize_skills(raw_job.get('skills')) or None,
                    url=raw_job.get('url'),
                    published_at=raw_job.get('published_at'),
                    scraped_at=raw_job.get('scraped_at', datetime.now())
                )

                # Guardar en BD
                self.repository.add(job)
                saved_count += 1
                logger.info(f"  ↳ ✅ Guardada oferta: {job.title}")

            except Exception as e:
                logger.exception(f"  ❌ Error guardando oferta '{job_title}': {e}")
                continue

        logger.info(f"\n📊 Resumen: {processed_count} procesadas, {saved_count} guardadas/enriquecidas")
        return saved_count

    def _merge_missing_fields(self, existing: Job, raw_job: dict) -> bool:
        """Completa campos vacios de una oferta existente con nueva data."""
        updated = False
        fields = [
            "title",
            "company",
            "city",
            "location_text",
            "contract_type",
            "work_mode",
            "english_required",
            "salary_min",
            "salary_max",
            "currency",
            "description",
            "skills",
            "published_at",
        ]

        for field in fields:
            current_value = getattr(existing, field)
            incoming_value = raw_job.get(field)
            if (current_value is None or current_value == "") and incoming_value not in (None, ""):
                if field == "skills":
                    incoming_value = normalize_skills(incoming_value) or None
                setattr(existing, field, incoming_value)
                updated = True

        return updated

    def get_scraping_stats(self) -> dict:
        """Estadísticas del scraping"""
        # Obtener todas las ofertas
        all_jobs = self.repository.get_all()

        stats = {
            'total_jobs': len(all_jobs),
            'sources': {},
            'cities': {},
            'companies': {}
        }
        logger.debug(f"Calculando estadísticas de scraping: total_jobs={len(all_jobs)}")

        for job in all_jobs:
            # Por fuente
            stats['sources'][job.source] = stats['sources'].get(job.source, 0) + 1

            # Por ciudad
            if job.city:
                stats['cities'][job.city] = stats['cities'].get(job.city, 0) + 1

            # Por empresa
            if job.company:
                stats['companies'][job.company] = stats['companies'].get(job.company, 0) + 1

        return stats