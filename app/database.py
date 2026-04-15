from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.logger import logger

# Configuración de la base de datos
DATABASE_URL = "postgresql://jobtrend:jobtrend@localhost:5432/jobtrend"

engine = create_engine(DATABASE_URL)
logger.info("Conexión a PostgreSQL configurada")
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