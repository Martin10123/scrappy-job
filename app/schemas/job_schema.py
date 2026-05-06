from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

class JobRead(BaseModel):
    id: int
    source: str
    title: str
    company: Optional[str]
    city: Optional[str]
    remote_type: Optional[str]
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
