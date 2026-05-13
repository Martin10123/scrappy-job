import os
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.jobs import router as jobs_router
from app.database import engine, Base, backfill_jobs_location_fields, sync_jobs_schema

# Cargar variables de ambiente
load_dotenv()

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)
sync_jobs_schema()
backfill_jobs_location_fields()

app = FastAPI(
    title="JobTrend AI",
    description="API para análisis de tendencias de empleo en tech",
    version="1.0.0",
)

# Configurar CORS
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

print(f"🔓 CORS Origins configurado: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])

@app.get("/")
def root():
    return {"message": "JobTrend AI API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}