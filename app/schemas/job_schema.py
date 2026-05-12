from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel

class JobRead(BaseModel):
    id: int
    source: str
    title: str
    company: Optional[str]
    city: Optional[str]
    location_text: Optional[str]
    contract_type: Optional[str]
    work_mode: Optional[str]
    english_required: Optional[bool]
    salary_min: Optional[int]
    salary_max: Optional[int]
    currency: Optional[str]
    description: Optional[str]
    category: Optional[str]
    seniority: Optional[str]
    skills: Optional[List[str]]
    url: Optional[str]
    published_at: Optional[datetime]
    scraped_at: Optional[datetime]

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[JobRead]


class ScrapeTriggerRequest(BaseModel):
    source: Optional[str] = None
    search_term: Optional[Union[str, List[str]]] = "desarrollador"
    location: Optional[str] = "colombia"
    max_pages: Optional[int] = 5


class ScrapeTriggerResponse(BaseModel):
    task_id: str
    status_url: str
    message: str
    source: Optional[str]
    search_term: Optional[Union[str, List[str]]]
    location: Optional[str]
    max_pages: int
    queued_sources: List[str]


class ScrapeStatusSource(BaseModel):
    status: str
    processed_jobs: int
    total_jobs: int
    saved_jobs: int
    progress_pct: float
    message: Optional[str] = None


class ScrapeStatusResponse(BaseModel):
    task_id: str
    status: str
    message: str
    queued_sources: List[str]
    total_sources: int
    completed_sources: int
    current_source: Optional[str]
    processed_jobs: int
    total_jobs: int
    saved_jobs: int
    progress_pct: float
    started_at: datetime
    updated_at: datetime
    sources: Dict[str, ScrapeStatusSource]


class ForecastPoint(BaseModel):
    month: str
    count: int


class SkillForecast(BaseModel):
    skill: str
    history: List[ForecastPoint]
    forecast: List[ForecastPoint]
    total_observed: int
    projected_total: int
    growth_pct: Optional[float]


class JobDemandForecastResponse(BaseModel):
    generated_at: datetime
    horizon_months: int
    top_n: int
    total_jobs_analyzed: int
    technical_skills: List[SkillForecast]
    soft_skills: List[SkillForecast]
    skills: List[SkillForecast]


class SkillForecastConfidence(BaseModel):
    skill: str
    train_points: int
    test_points: int
    mae: float
    mape_pct: Optional[float]
    confidence_level: str


class JobForecastConfidenceResponse(BaseModel):
    generated_at: datetime
    top_n: int
    test_horizon_months: int
    total_jobs_analyzed: int
    technical_skills: List[SkillForecastConfidence]
    soft_skills: List[SkillForecastConfidence]
    skills: List[SkillForecastConfidence]
