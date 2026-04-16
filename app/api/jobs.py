from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.logger import logger
from app.repositories.job_repository import JobRepository
from app.services.job_service import JobService
from app.services.scraping_service import ScrapingService
from app.schemas.job_schema import JobRead

router = APIRouter()

@router.get("/", response_model=List[JobRead])
def list_jobs(db: Session = Depends(get_db)):
    logger.info("Solicitando lista de jobs")
    repository = JobRepository(db)
    service = JobService(repository)
    jobs = service.list_jobs()
    logger.info(f"Se encontraron {len(jobs)} jobs")
    return jobs

@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db)):
    repository = JobRepository(db)
    service = JobService(repository)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/scrape/{source}")
def scrape_jobs(source: str, background_tasks: BackgroundTasks,
                search_term: str = "desarrollador", location: str = "colombia",
                max_pages: int = 5, db: Session = Depends(get_db)):
    """
    Ejecutar scraping de ofertas desde una fuente específica
    """
    max_pages = max(max_pages, 5)

    repository = JobRepository(db)
    scraping_service = ScrapingService(repository)

    logger.info(f"Iniciando scraping en background: source={source}, search_term={search_term}, location={location}, max_pages={max_pages}")
    background_tasks.add_task(
        scraping_service.scrape_and_save_jobs,
        source=source,
        search_term=search_term,
        location=location,
        max_pages=max_pages
    )

    return {
        "message": f"Scraping de {source} iniciado en background",
        "search_term": search_term,
        "location": location,
        "max_pages": max_pages
    }

@router.get("/stats/scraping")
def get_scraping_stats(db: Session = Depends(get_db)):
    """Obtener estadísticas del scraping"""
    repository = JobRepository(db)
    scraping_service = ScrapingService(repository)
    stats = scraping_service.get_scraping_stats()
    return stats
