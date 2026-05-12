from datetime import datetime
from typing import List, Optional

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
