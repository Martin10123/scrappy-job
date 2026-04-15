#!/usr/bin/env python3
"""
Script para ejecutar scraping manualmente
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database import get_db_session
from app.repositories.job_repository import JobRepository
from app.services.scraping_service import ScrapingService

def run_scraping():
    """Ejecutar scraping de Magneto365"""
    print("🚀 Iniciando scraping de Magneto365...")

    # Obtener sesión de BD
    db = get_db_session()

    try:
        # Crear servicios
        repository = JobRepository(db)
        scraping_service = ScrapingService(repository)

        # Ejecutar scraping
        saved_count = scraping_service.scrape_and_save_jobs(
            source='magneto365',
            search_term='desarrollador',
            location='colombia',
            max_pages=2  # Solo 2 páginas para prueba
        )

        print(f"✅ Scraping completado. {saved_count} ofertas guardadas.")

        # Mostrar estadísticas
        stats = scraping_service.get_scraping_stats()
        print("\n📊 Estadísticas:")
        print(f"   Total ofertas: {stats['total_jobs']}")
        print(f"   Fuentes: {stats['sources']}")
        print(f"   Top ciudades: {dict(sorted(stats['cities'].items(), key=lambda x: x[1], reverse=True)[:5])}")

    except Exception as e:
        print(f"❌ Error durante scraping: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_scraping()