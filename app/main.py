from fastapi import FastAPI

from app.api.jobs import router as jobs_router
from app.database import engine, Base

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(title="JobTrend AI")

app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])

@app.get("/")
def root():
    return {"message": "JobTrend AI API"}
