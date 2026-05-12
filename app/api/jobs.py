from datetime import datetime
from threading import Lock
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.logger import logger
from app.database import get_db_session
from app.repositories.job_repository import JobRepository
from app.services.job_service import JobService
from app.services.scraping_service import ScrapingService
from app.schemas.job_schema import JobDemandForecastResponse, JobForecastConfidenceResponse, JobListResponse, JobRead, ScrapeStatusResponse, ScrapeTriggerRequest, ScrapeTriggerResponse

router = APIRouter()

_SCRAPE_TASKS = {}
_SCRAPE_TASKS_LOCK = Lock()


def _ensure_task(task_id: str) -> dict:
    with _SCRAPE_TASKS_LOCK:
        task = _SCRAPE_TASKS.get(task_id)
        if task is None:
            raise KeyError(task_id)
        return task


def _update_task(task_id: str, **updates) -> None:
    with _SCRAPE_TASKS_LOCK:
        task = _SCRAPE_TASKS.get(task_id)
        if not task:
            return
        task.update(updates)
        task["updated_at"] = datetime.utcnow()


def _recompute_task_aggregate(task_id: str) -> None:
    with _SCRAPE_TASKS_LOCK:
        task = _SCRAPE_TASKS.get(task_id)
        if not task:
            return

        sources = task["sources"]
        processed_jobs = sum(source["processed_jobs"] for source in sources.values())
        total_jobs = sum(source["total_jobs"] for source in sources.values())
        saved_jobs = sum(source["saved_jobs"] for source in sources.values())

        completed_sources = sum(1 for source in sources.values() if source["status"] in {"completed", "error"})
        current_sources = [name for name, source in sources.items() if source["status"] == "running"]

        if total_jobs > 0:
            progress_pct = round((processed_jobs / total_jobs) * 100.0, 2)
        else:
            progress_pct = round((completed_sources / max(task["total_sources"], 1)) * 100.0, 2)

        overall_status = "running"
        if completed_sources == task["total_sources"]:
            has_error = any(source["status"] == "error" for source in sources.values())
            overall_status = "completed_with_errors" if has_error else "completed"

        task["processed_jobs"] = processed_jobs
        task["total_jobs"] = total_jobs
        task["saved_jobs"] = saved_jobs
        task["completed_sources"] = completed_sources
        task["current_source"] = current_sources[0] if current_sources else None
        task["progress_pct"] = progress_pct
        task["status"] = overall_status
        task["updated_at"] = datetime.utcnow()


def _run_scrape_background(task_id: str, source: str, search_term: str, location: str, max_pages: int) -> None:
    def on_progress(payload: dict) -> None:
        with _SCRAPE_TASKS_LOCK:
            task = _SCRAPE_TASKS.get(task_id)
            if not task:
                return

            source_progress = task["sources"][source]
            source_progress["status"] = payload.get("status", source_progress["status"])
            source_progress["processed_jobs"] = int(payload.get("processed_jobs", source_progress["processed_jobs"]))
            source_progress["total_jobs"] = int(payload.get("total_jobs", source_progress["total_jobs"]))
            source_progress["saved_jobs"] = int(payload.get("saved_jobs", source_progress["saved_jobs"]))
            source_progress["message"] = payload.get("message", source_progress.get("message"))
            if source_progress["total_jobs"] > 0:
                source_progress["progress_pct"] = round(
                    (source_progress["processed_jobs"] / source_progress["total_jobs"]) * 100.0,
                    2,
                )
            elif source_progress["status"] in {"completed", "error"}:
                source_progress["progress_pct"] = 100.0

            task["message"] = f"Procesando fuente: {source}"
            task["updated_at"] = datetime.utcnow()

        _recompute_task_aggregate(task_id)

    _update_task(task_id, status="running", message=f"Iniciando fuente: {source}")
    with _SCRAPE_TASKS_LOCK:
        if task_id in _SCRAPE_TASKS:
            _SCRAPE_TASKS[task_id]["sources"][source]["status"] = "running"

    db = get_db_session()
    try:
        repository = JobRepository(db)
        scraping_service = ScrapingService(repository)
        scraping_service.scrape_and_save_jobs(
            source=source,
            search_term=search_term,
            location=location,
            max_pages=max_pages,
            progress_callback=on_progress,
        )
        with _SCRAPE_TASKS_LOCK:
            task = _SCRAPE_TASKS.get(task_id)
            if task:
                task["sources"][source]["status"] = "completed"
                task["sources"][source]["progress_pct"] = 100.0
                task["sources"][source]["message"] = "Fuente completada"
                task["updated_at"] = datetime.utcnow()
    except Exception as exc:
        logger.exception(f"Error en background scraping source={source}")
        with _SCRAPE_TASKS_LOCK:
            task = _SCRAPE_TASKS.get(task_id)
            if task:
                task["sources"][source]["status"] = "error"
                task["sources"][source]["message"] = str(exc)
                task["updated_at"] = datetime.utcnow()
    finally:
        db.close()
        _recompute_task_aggregate(task_id)


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
    contract_type: Optional[str] = Query(default=None),
    work_mode: Optional[str] = Query(default=None),
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
        contract_type=contract_type,
        work_mode=work_mode,
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

@router.post("/scrape/source/{source}")
def scrape_jobs(source: str, background_tasks: BackgroundTasks,
                search_term: str = "desarrollador", location: str = "colombia",
                max_pages: int = 5, db: Session = Depends(get_db)):
    """
    Ejecutar scraping de ofertas desde una fuente específica
    """
    max_pages = max(max_pages, 5)

    task_id = str(uuid4())
    now = datetime.utcnow()
    with _SCRAPE_TASKS_LOCK:
        _SCRAPE_TASKS[task_id] = {
            "task_id": task_id,
            "status": "queued",
            "message": "Scraping encolado",
            "queued_sources": [source],
            "total_sources": 1,
            "completed_sources": 0,
            "current_source": None,
            "processed_jobs": 0,
            "total_jobs": 0,
            "saved_jobs": 0,
            "progress_pct": 0.0,
            "started_at": now,
            "updated_at": now,
            "sources": {
                source: {
                    "status": "queued",
                    "processed_jobs": 0,
                    "total_jobs": 0,
                    "saved_jobs": 0,
                    "progress_pct": 0.0,
                    "message": "Pendiente",
                }
            },
        }

    logger.info(f"Iniciando scraping en background: source={source}, search_term={search_term}, location={location}, max_pages={max_pages}, task_id={task_id}")
    background_tasks.add_task(
        _run_scrape_background,
        task_id=task_id,
        source=source,
        search_term=search_term,
        location=location,
        max_pages=max_pages,
    )

    return {
        "task_id": task_id,
        "status_url": f"/jobs/scrape/status/{task_id}",
        "message": f"Scraping de {source} iniciado en background",
        "source": source,
        "search_term": search_term,
        "location": location,
        "max_pages": max_pages,
        "queued_sources": [source],
    }


@router.post("/scrape/run", response_model=ScrapeTriggerResponse, status_code=202)
def trigger_scrape(
    payload: ScrapeTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Endpoint para que el front dispare scraping con un click."""
    queued_sources = [payload.source] if payload.source else ["magneto365", "computrabajo", "getonboard"]

    logger.info(
        "Disparando scraping desde el front: "
        f"source={payload.source} search_term={payload.search_term} location={payload.location} max_pages={payload.max_pages}"
    )

    task_id = str(uuid4())
    now = datetime.utcnow()
    with _SCRAPE_TASKS_LOCK:
        _SCRAPE_TASKS[task_id] = {
            "task_id": task_id,
            "status": "queued",
            "message": "Scraping encolado desde el front",
            "queued_sources": queued_sources,
            "total_sources": len(queued_sources),
            "completed_sources": 0,
            "current_source": None,
            "processed_jobs": 0,
            "total_jobs": 0,
            "saved_jobs": 0,
            "progress_pct": 0.0,
            "started_at": now,
            "updated_at": now,
            "sources": {
                source: {
                    "status": "queued",
                    "processed_jobs": 0,
                    "total_jobs": 0,
                    "saved_jobs": 0,
                    "progress_pct": 0.0,
                    "message": "Pendiente",
                }
                for source in queued_sources
            },
        }

    for source in queued_sources:
        background_tasks.add_task(
            _run_scrape_background,
            task_id=task_id,
            source=source,
            search_term=payload.search_term or "desarrollador",
            location=payload.location or "colombia",
            max_pages=payload.max_pages or 5,
        )

    return {
        "task_id": task_id,
        "status_url": f"/jobs/scrape/status/{task_id}",
        "message": "Scraping encolado desde el front",
        "source": payload.source,
        "search_term": payload.search_term,
        "location": payload.location,
        "max_pages": payload.max_pages or 5,
        "queued_sources": queued_sources,
    }


@router.get("/scrape/status/{task_id}", response_model=ScrapeStatusResponse)
def get_scrape_status(task_id: str):
    try:
        task = _ensure_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Scrape task not found")

    return task

@router.get("/stats/scraping")
def get_scraping_stats(db: Session = Depends(get_db)):
    """Obtener estadísticas del scraping"""
    repository = JobRepository(db)
    scraping_service = ScrapingService(repository)
    stats = scraping_service.get_scraping_stats()
    return stats
