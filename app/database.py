import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
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
logger.info(f"Conexión a PostgreSQL configurada en {DB_HOST}:{DB_PORT}/{DB_NAME}")
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