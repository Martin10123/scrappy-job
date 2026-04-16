from typing import List, Optional
from sqlalchemy.orm import Session

from app.logger import logger
from app.models.job import Job

class JobRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> List[Job]:
        logger.debug("JobRepository: consultando todos los jobs")
        jobs = self.session.query(Job).all()
        logger.debug(f"JobRepository: recuperados {len(jobs)} jobs")
        return jobs

    def get_by_id(self, job_id: int) -> Optional[Job]:
        logger.debug(f"JobRepository: consultando job por id={job_id}")
        job = self.session.query(Job).filter(Job.id == job_id).first()
        if job:
            logger.debug(f"JobRepository: encontrado job id={job_id}")
        else:
            logger.debug(f"JobRepository: no se encontró job id={job_id}")
        return job

    def get_by_url(self, url: str) -> Optional[Job]:
        """Buscar oferta por URL para evitar duplicados"""
        logger.debug(f"JobRepository: consultando job por url={url}")
        job = self.session.query(Job).filter(Job.url == url).first()
        if job:
            logger.debug("JobRepository: job encontrado por url")
        else:
            logger.debug("JobRepository: no se encontró job por url")
        return job

    def add(self, job: Job) -> Job:
        logger.debug(f"JobRepository: guardando job title={job.title}")
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        logger.info(f"JobRepository: job guardado id={job.id} title={job.title}")
        return job

    def update(self, job: Job) -> Job:
        logger.debug(f"JobRepository: actualizando job id={job.id}")
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        logger.info(f"JobRepository: job actualizado id={job.id}")
        return job
