from typing import List, Optional

from app.logger import logger
from app.models.job import Job
from app.repositories.job_repository import JobRepository

class JobService:
    def __init__(self, repository: JobRepository):
        self.repository = repository

    def list_jobs(self) -> List[Job]:
        logger.debug("JobService: solicitando listado de jobs")
        jobs = self.repository.get_all()
        logger.info(f"JobService: {len(jobs)} jobs recuperados")
        return jobs

    def get_job(self, job_id: int) -> Optional[Job]:
        logger.debug(f"JobService: solicitando job id={job_id}")
        job = self.repository.get_by_id(job_id)
        if job:
            logger.info(f"JobService: job encontrado id={job_id} title={job.title}")
        else:
            logger.warning(f"JobService: job no encontrado id={job_id}")
        return job
