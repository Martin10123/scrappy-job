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
    """Ejecutar scraping de múltiples fuentes"""
    print("🚀 Iniciando scraping de múltiples plataformas...")

    # Obtener sesión de BD
    db = get_db_session()

    try:
        # Crear servicios
        repository = JobRepository(db)
        scraping_service = ScrapingService(repository)

        # Términos de búsqueda comunes
        search_terms = ["desarrollador", "frontend", "backend", "python", "react", "Programación", "Desarrollador mobile", "DevOps", "Data Science"]

        # Ejecutar scraping de Magneto365
        print("\n🌐 Scrapeando Magneto365...")
        try:
            saved_magneto = scraping_service.scrape_and_save_jobs(
                source='magneto365',
                search_term=search_terms,
                location='colombia',
                max_pages=3
            )
            print(f"✅ Magneto365: {saved_magneto} ofertas guardadas")
        except Exception as e:
            print(f"❌ Error en Magneto365: {e}")

        # Ejecutar scraping de GetOnBoard
        print("\n🌐 Scrapeando GetOnBoard (esto puede tardar un poco)...")
        try:
            from scrapers.getonboard.scraper import run_getonboard_scraper
            from app.models.job import Job
            from datetime import datetime
            
            print(f"📍 Extrayendo ofertas de GetOnBoard...")
            raw_jobs = run_getonboard_scraper(search_terms=search_terms, max_pages=2)
            print(f"🔍 GetOnBoard scraper retornó: {len(raw_jobs)} ofertas extraídas")
            
            if raw_jobs:
                print(f"📋 Primeras 3 ofertas:")
                for i, job in enumerate(raw_jobs[:3], 1):
                    print(f"   {i}. {job.get('title')} (URL: {job.get('url')[:60] if job.get('url') else 'SIN URL'}...)")
            
            print(f"\n💾 Guardando {len(raw_jobs)} ofertas en BD...")
            saved_getonboard = 0
            for raw_job in raw_jobs:
                try:
                    existing = repository.get_by_url(raw_job.get('url'))
                    if existing:
                        print(f"  ⏭️  {raw_job.get('title')} (ya existe)")
                        continue
                    
                    job = Job(
                        source='getonboard',
                        title=raw_job.get('title'),
                        company=raw_job.get('company'),
                        city=raw_job.get('city'),
                        remote_type=raw_job.get('remote_type'),
                        salary_min=raw_job.get('salary_min'),
                        salary_max=raw_job.get('salary_max'),
                        currency=raw_job.get('currency'),
                        description=raw_job.get('description'),
                        skills=raw_job.get('skills'),
                        url=raw_job.get('url'),
                        published_at=raw_job.get('published_at'),
                        scraped_at=raw_job.get('scraped_at', datetime.now())
                    )
                    repository.add(job)
                    saved_getonboard += 1
                except Exception as e:
                    print(f"  ❌ Error guardando {raw_job.get('title')}: {e}")
            
            print(f"✅ GetOnBoard: {saved_getonboard} ofertas guardadas")
        except Exception as e:
            import traceback
            print(f"❌ Error en GetOnBoard: {e}")
            traceback.print_exc()

        # Mostrar estadísticas finales
        stats = scraping_service.get_scraping_stats()
        print("\n📊 Estadísticas finales:")
        print(f"   Total ofertas: {stats['total_jobs']}")
        print(f"   Fuentes: {stats['sources']}")
        print(f"   Top ciudades: {dict(sorted(stats['cities'].items(), key=lambda x: x[1], reverse=True)[:5])}")

    except Exception as e:
        print(f"❌ Error durante scraping: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_scraping()