from sqlalchemy import Column, DateTime, Integer, JSON, String

from app.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    title = Column(String, nullable=False)
    company = Column(String)
    city = Column(String)
    remote_type = Column(String)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    currency = Column(String)
    description = Column(String)
    category = Column(String)
    seniority = Column(String)
    skills = Column(JSON)
    url = Column(String, unique=True, index=True)
    published_at = Column(DateTime)
    scraped_at = Column(DateTime)
