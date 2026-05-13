import asyncio
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    raise ImportError("Playwright no está instalado. Ejecuta: pip install playwright")

from app.logger import logger
from app.services.job_normalizer import detect_english_requirement, detect_work_mode, extract_city_from_location, normalize_location_text

class GetOnBoardScraper:
    """Scraper para GetOnBoard usando Playwright para JS rendering"""

    def __init__(self):
        self.base_url = "https://www.getonbrd.com"
        self.jobs_url = f"{self.base_url}/empleos"
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def get_jobs(self, search_terms: Optional[List[str]] = None, max_pages: int = 3) -> List[Dict]:
        """
        Extrae ofertas de empleo de GetOnBoard

        Args:
            search_terms: Lista de términos de búsqueda (ej: ["desarrollador", "frontend", "backend"])
            max_pages: Número máximo de páginas a scrapear por término

        Returns:
            Lista de diccionarios con datos de las ofertas
        """
        if search_terms is None:
            search_terms = ["desarrollador", "frontend", "backend"]
        elif isinstance(search_terms, str):
            search_terms = [search_terms]

        jobs = []
        seen_urls = set()

        try:
            async with async_playwright() as p:
                logger.info("Lanzando navegador Chromium...")
                self.browser = await p.chromium.launch(headless=True)
                logger.info("✅ Navegador lanzado. Creando contexto...")
                self.context = await self.browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                logger.info("✅ Contexto creado.")

                for search_term in search_terms:
                    logger.info(f"🔍 Iniciando búsqueda en GetOnBoard para término: '{search_term}'")

                    page = await self.context.new_page()
                    try:
                        # Navegar a la página de búsqueda
                        logger.info(f"📄 Navegando a {self.jobs_url}...")
                        await page.goto(self.jobs_url, wait_until="networkidle", timeout=30000)
                        logger.info("✅ Página cargada.")
                        logger.info("⏳ Esperando 3 segundos para estabilizar...")
                        await asyncio.sleep(3)  # Esperar 3 segundos para estabilizar

                        # Rellenar el formulario de búsqueda
                        logger.info(f"🔤 Buscando elemento input #search_term...")
                        search_input = page.locator("#search_term")
                        logger.info(f"📝 Escribiendo término: '{search_term}'...")
                        await search_input.fill(search_term)
                        await asyncio.sleep(1)

                        # Hacer clic en buscar o presionar Enter
                        logger.info("🔎 Presionando Enter...")
                        await search_input.press("Enter")
                        logger.info("⏳ Esperando 5 segundos para que carguen resultados...")
                        await asyncio.sleep(5)  # Esperar 5 segundos para que carguen resultados
                        logger.info("✅ Resultados esperados.")

                        # Extraer ofertas de múltiples páginas
                        for page_num in range(1, max_pages + 1):
                            logger.info(f"📋 Scrapeando página {page_num} para '{search_term}'...")

                            page_jobs = await self._extract_jobs_from_page(page)
                            logger.info(f"📍 Página {page_num}: encontradas {len(page_jobs)} ofertas.")
                            
                            # Filtrar duplicados por URL
                            new_jobs = []
                            for job in page_jobs:
                                job_url = job.get("url")
                                if job_url and job_url not in seen_urls:
                                    seen_urls.add(job_url)
                                    new_jobs.append(job)

                            jobs.extend(new_jobs)

                            if not page_jobs or page_num >= max_pages:
                                logger.info(f"🛑 Deteniendo: sin más ofertas o llegó a max_pages={max_pages}")
                                break

                            # Ir a la siguiente página
                            try:
                                logger.info(f"➡️  Buscando botón 'siguiente'...")
                                next_button = page.locator("a[rel='next']")
                                if await next_button.is_visible():
                                    logger.info(f"👆 Haciendo clic en 'siguiente'...")
                                    await next_button.click()
                                    logger.info(f"⏳ Esperando 5 segundos para siguiente página...")
                                    await asyncio.sleep(5)
                                else:
                                    logger.info(f"🛑 No hay botón 'siguiente'. Fin del scraping.")
                                    break
                            except Exception as e:
                                logger.warning(f"No hay siguiente página: {e}")
                                break

                    except Exception as e:
                        logger.exception(f"Error procesando búsqueda para '{search_term}': {e}")
                    finally:
                        logger.info(f"❌ Cerrando página para '{search_term}'.")
                        await page.close()

                    # Pausa entre términos de búsqueda
                    logger.info(f"⏳ Pausa de 3 segundos antes del siguiente término...")
                    await asyncio.sleep(3)

        except Exception as e:
            logger.exception(f"Error en GetOnBoard scraper: {e}")
        finally:
            logger.info("🧹 Limpiando recursos...")
            if self.context:
                logger.info("  - Cerrando contexto...")
                try:
                    await self.context.close()
                except Exception as context_err:
                    logger.warning(f"  - Contexto ya estaba cerrado o no disponible: {context_err}")
                finally:
                    self.context = None
            if self.browser:
                logger.info("  - Cerrando navegador...")
                try:
                    if self.browser.is_connected():
                        await self.browser.close()
                except Exception as browser_err:
                    logger.warning(f"  - Navegador ya estaba cerrado o no disponible: {browser_err}")
                finally:
                    self.browser = None
            logger.info("✅ Recursos limpios.")

        logger.info(f"✅ Scraping GetOnBoard completado: {len(jobs)} ofertas únicas encontradas")
        return jobs

    async def _extract_jobs_from_page(self, page: Page) -> List[Dict]:
        """Extrae las tarjetas de ofertas de la página actual"""
        jobs: List[Dict] = []

        try:
            # Obtener HTML de la página
            logger.info("📄 Extrayendo contenido HTML de la página...")
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            logger.info(f"✅ HTML extraído ({len(html_content)} caracteres)")

            # Buscar todas las tarjetas de oferta
            logger.info("🔎 Buscando enlaces con patrón /empleos/...")
            job_cards = soup.find_all(
                "a",
                href=re.compile(r"/empleos/")
            )
            logger.info(f"📍 Encontrados {len(job_cards)} enlaces con /empleos/")

            # Filtrar para obtener solo enlaces de ofertas (no de categorías)
            job_links = [
                card for card in job_cards
                if "/tag/" not in card.get("href", "") and "/ciudad/" not in card.get("href", "")
            ]
            logger.info(f"✅ Después de filtrar: {len(job_links)} enlaces válidos")

            for idx, link in enumerate(job_links[:10]):  # Limitar a 10 ofertas por página
                try:
                    job_url = link.get("href", "")
                    if not job_url:
                        continue

                    if not job_url.startswith("http"):
                        job_url = self.base_url + job_url

                    logger.info(f"  [{idx+1}] 🔗 Extrayendo detalle de: {job_url[:80]}...")
                    # Extraer datos básicos del card
                    job_data = await self._extract_job_detail(job_url)

                    if job_data and job_data.get("title"):
                        logger.info(f"  [{idx+1}] ✅ Guardado: {job_data.get('title')}")
                        jobs.append(job_data)
                    else:
                        logger.warning(f"  [{idx+1}] ⚠️ Sin datos o sin título")

                except Exception as e:
                    logger.warning(f"  [{idx+1}] ❌ Error extrayendo job: {e}")
                    continue

            logger.info(f"📊 Total extraídos de esta página: {len(jobs)} ofertas")

        except Exception as e:
            logger.exception(f"Error en _extract_jobs_from_page: {e}")

        return jobs

    async def _extract_job_detail(self, job_url: str) -> Optional[Dict]:
        """Navega a la oferta y extrae detalles completos"""
        detail_page = None
        try:
            logger.debug(f"    🌐 Abriendo nueva página para: {job_url[:60]}...")
            detail_page = await self.context.new_page()
            logger.debug(f"    ⏳ Navegando a {job_url[:60]}...")
            await detail_page.goto(job_url, wait_until="networkidle", timeout=30000)
            logger.debug(f"    ✅ Página cargada. Esperando 3 segundos...")
            await asyncio.sleep(3)  # Esperar 3 segundos para que cargue completamente
            logger.debug(f"    📄 Extrayendo HTML...")

            # Obtener HTML de la página de detalle
            html_content = await detail_page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            logger.debug(f"    ✅ HTML extraído ({len(html_content)} bytes)")

            # Extraer datos usando microdata schema.org
            title = None
            title_elem = soup.find(attrs={"itemprop": "title"})
            if title_elem:
                title = title_elem.get_text(strip=True)

            company = None
            company_elem = soup.find(attrs={"itemprop": "name"}, attrs_in_scope={"hiringOrganization"})
            if not company_elem:
                company_elem = soup.find("a", class_=lambda x: x and "header__company" in x if x else False)
            if company_elem:
                company = company_elem.get_text(strip=True)

            # Extraer ubicación y modalidad de trabajo
            location_text = None
            city = None
            work_mode = None
            
            # Buscar elemento de ubicación (jobLocation)
            location_elem = soup.find(attrs={"itemprop": "address"})
            if location_elem:
                location_text = normalize_location_text(location_elem.get_text(" ", strip=True))
                city = extract_city_from_location(location_text)
            
            # Extraer modalidad de trabajo de diferentes fuentes en GetOnBoard
            # 1. Buscar en el elemento jobLocation que puede contener "(Remoto)", "(Híbrido)", etc.
            job_location = soup.find(attrs={"itemprop": "jobLocation"})
            if job_location and not work_mode:
                location_full_text = job_location.get_text(" ", strip=True)
                work_mode = detect_work_mode(location_full_text, None)
            
            # 2. Buscar específicamente span con ícono de wifi (significa Remoto)
            if not work_mode:
                wifi_icon = soup.find("i", class_=lambda x: x and "icon-wifi" in x if x else False)
                if wifi_icon:
                    parent = wifi_icon.find_parent()
                    if parent:
                        text = parent.get_text(" ", strip=True).lower()
                        if "remoto" in text or "remote" in text:
                            work_mode = "remote"
            
            # 3. Buscar en location-tooltip-content que puede contener info de modalidad
            if not work_mode:
                tooltip = soup.find(class_=lambda x: x and "location-tooltip-content" in x if x else False)
                if tooltip:
                    tooltip_text = tooltip.get_text(" ", strip=True)
                    work_mode = detect_work_mode(tooltip_text, None)

            # Extraer tipo de empleo/contrato
            employment_type = None
            employment_elem = soup.find(attrs={"itemprop": "employmentType"})
            if employment_elem:
                employment_type = employment_elem.get("content", employment_elem.get_text(strip=True))
            
            # Fallback: si aún no hay work_mode, usar el método anterior
            if not work_mode:
                work_mode = detect_work_mode(location_text, employment_type)

            # Extraer salario
            salary_min = salary_max = currency = None
            salary_elem = soup.find(attrs={"itemprop": "baseSalary"})
            if salary_elem:
                salary_text = salary_elem.get_text(strip=True)
                # Buscar patrón de salario "$X - $Y"
                numbers = re.findall(r"\$?([\d.,]+)", salary_text)
                if len(numbers) >= 2:
                    try:
                        salary_min = int(numbers[0].replace(",", "").replace(".", ""))
                        salary_max = int(numbers[1].replace(",", "").replace(".", ""))
                    except ValueError:
                        pass
                # Detectar moneda
                if "USD" in salary_text:
                    currency = "USD"
                elif "$" in salary_text and "COP" not in salary_text:
                    currency = "USD"  # GetOnBoard es principalmente USD
                else:
                    currency = "USD"

            # Extraer descripción
            description = None
            desc_elem = soup.find(attrs={"itemprop": "description"})
            if desc_elem:
                description = desc_elem.get_text("\n", strip=True)
            else:
                # Alternativa: buscar por id
                job_body = soup.find(id="job-body")
                if job_body:
                    description = job_body.get_text("\n", strip=True)

            english_required = detect_english_requirement(title, description, location_text)

            # Extraer skills/tags
            skills: List[str] = []
            skills_section = soup.find(attrs={"itemprop": "skills"})
            if skills_section:
                skill_tags = skills_section.find_all(class_=lambda x: x and "gb-tags__item" in x if x else False)
                for tag in skill_tags:
                    skill = tag.get_text(strip=True)
                    if skill:
                        skills.append(skill)

            # Extraer fecha de publicación
            published_at = None
            date_elem = soup.find(attrs={"itemprop": "datePosted"})
            if date_elem:
                date_str = date_elem.get("datetime", date_elem.get_text(strip=True))
                try:
                    published_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    published_at = datetime.now()

            return {
                'source': 'getonboard',
                'title': title,
                'company': company,
                'city': city,
                'location_text': location_text,
                'contract_type': employment_type,
                'work_mode': work_mode,
                'url': job_url,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'currency': currency,
                'description': description,
                'english_required': english_required,
                'skills': skills if skills else None,
                'published_at': published_at or datetime.now(),
                'scraped_at': datetime.now()
            }
        except Exception as e:
            logger.warning(f"    ❌ Error extrayendo detalle de {job_url}: {e}")
            return None
        finally:
            if detail_page:
                try:
                    logger.debug(f"    🔒 Cerrando página de detalle...")
                    await detail_page.close()
                except Exception as close_err:
                    logger.warning(f"    ⚠️ Error cerrando página: {close_err}")


def run_getonboard_scraper(search_terms: Optional[List[str]] = None, max_pages: int = 3) -> List[Dict]:
    """Función síncrona para ejecutar el scraper async de GetOnBoard"""
    scraper = GetOnBoardScraper()
    return asyncio.run(scraper.get_jobs(search_terms=search_terms, max_pages=max_pages))
