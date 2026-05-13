import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.logger import logger

# Carga variables del archivo .env en la raiz del proyecto.
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "jobtrend")
DB_USER = os.getenv("DB_USER", "jobtrend")
DB_PASSWORD = os.getenv("DB_PASSWORD", "jobtrend")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Función para obtener una sesión de base de datos (para FastAPI dependencies)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Función para obtener una sesión simple (para scripts)
def get_db_session():
    return SessionLocal()


def sync_jobs_schema() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("jobs"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("jobs")}
    statements = []

    if "remote_type" in existing_columns and "contract_type" not in existing_columns:
        statements.append('ALTER TABLE jobs RENAME COLUMN remote_type TO contract_type')
        existing_columns.remove("remote_type")
        existing_columns.add("contract_type")

    if "location_text" not in existing_columns:
        statements.append('ALTER TABLE jobs ADD COLUMN location_text VARCHAR')
    if "work_mode" not in existing_columns:
        statements.append('ALTER TABLE jobs ADD COLUMN work_mode VARCHAR')
    if "english_required" not in existing_columns:
        statements.append('ALTER TABLE jobs ADD COLUMN english_required BOOLEAN')

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def backfill_jobs_location_fields() -> None:
    from app.models.job import Job
    from app.services.job_normalizer import detect_english_requirement, detect_work_mode, extract_city_from_location, normalize_location_text

    session = SessionLocal()
    try:
        jobs = session.query(Job).all()
        updated = False

        for job in jobs:
            location_source = job.location_text or job.city
            normalized_location = normalize_location_text(location_source)
            normalized_city = extract_city_from_location(normalized_location)
            derived_work_mode = detect_work_mode(normalized_location, job.contract_type)

            if normalized_location and job.location_text != normalized_location:
                job.location_text = normalized_location
                updated = True

            if normalized_city and job.city != normalized_city:
                job.city = normalized_city
                updated = True
            elif derived_work_mode == "remote" and job.city and not normalized_city:
                job.city = None
                updated = True

            if derived_work_mode and job.work_mode != derived_work_mode:
                job.work_mode = derived_work_mode
                updated = True

            derived_english_required = detect_english_requirement(job.title, job.description, job.location_text)
            if derived_english_required is not None and job.english_required != derived_english_required:
                job.english_required = derived_english_required
                updated = True

        if updated:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()