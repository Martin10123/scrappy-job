from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.logger import logger
from app.repositories.job_repository import JobRepository
from app.services.job_service import JobService
from app.services.scraping_service import ScrapingService
from app.schemas.job_schema import JobDemandForecastResponse, JobForecastConfidenceResponse, JobListResponse, JobRead

router = APIRouter()

@router.get("/", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)):
    logger.info("Solicitando lista de jobs")
    repository = JobRepository(db)
    service = JobService(repository)
    jobs, _ = service.list_jobs(limit=5000, offset=0)
    logger.info(f"Se encontraron {len(jobs)} jobs")
    return jobs


@router.get("/search", response_model=JobListResponse)
def search_jobs(
    source: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    remote_type: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    logger.info("Solicitando lista paginada de jobs")
    repository = JobRepository(db)
    service = JobService(repository)
    jobs, total = service.list_jobs(
        source=source,
        city=city,
        remote_type=remote_type,
        search=search,
        limit=limit,
        offset=offset,
    )
    logger.info(f"Se encontraron {len(jobs)} jobs paginados")
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": jobs,
    }


@router.get("/analytics/overview")
def get_jobs_analytics_overview(
    source: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    top_n: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    repository = JobRepository(db)
    service = JobService(repository)
    return service.get_analytics_overview(source=source, city=city, top_n=top_n)


@router.get("/analytics/forecast", response_model=JobDemandForecastResponse)
def get_jobs_demand_forecast(
    source: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    top_n: int = Query(default=10, ge=1, le=50),
    months_ahead: int = Query(default=3, ge=1, le=12),
    db: Session = Depends(get_db),
):
    repository = JobRepository(db)
    service = JobService(repository)
    return service.get_demand_forecast(
        source=source,
        city=city,
        top_n=top_n,
        months_ahead=months_ahead,
    )


@router.get("/analytics/forecast-confidence", response_model=JobForecastConfidenceResponse)
def get_jobs_forecast_confidence(
    source: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    top_n: int = Query(default=10, ge=1, le=50),
    test_horizon_months: int = Query(default=2, ge=1, le=6),
    db: Session = Depends(get_db),
):
    repository = JobRepository(db)
    service = JobService(repository)
    return service.get_forecast_confidence(
        source=source,
        city=city,
        top_n=top_n,
        test_horizon_months=test_horizon_months,
    )


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
