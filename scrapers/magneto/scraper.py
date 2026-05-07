import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
from datetime import datetime
import re
from requests.exceptions import RequestException

from app.logger import logger

class MagnetoScraper:
    """Scraper para Magneto365"""

    def __init__(self):
        self.base_url = "https://www.magneto365.com"
        self.session = requests.Session()
        # Headers para simular navegador
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_jobs(self, search_term=None, location: str = "colombia", max_pages: int = 5) -> List[Dict]:
        """
        Extrae ofertas de empleo de Magneto365

        Args:
            search_term: Término(s) de búsqueda. Puede ser:
                - str: Un único término (ej: "desarrollador")
                - list: Múltiples términos (ej: ["desarrollador", "frontend", "backend"])
            location: Ubicación (ej: "colombia", "bogota")
            max_pages: Número máximo de páginas a scrapear por término

        Returns:
            Lista de diccionarios con datos de las ofertas
        """
        # Valores por defecto
        if search_term is None:
            search_term = ["desarrollador", "frontend", "backend", "python", "react", "java", "fullstack", "software"]
        elif isinstance(search_term, str):
            search_term = [search_term]
        
        jobs = []
        max_pages = max(max_pages, 5)
        seen_urls = set()

        # Iterar sobre cada término de búsqueda
        for term in search_term:
            logger.info(f"🔍 Iniciando búsqueda para término: '{term}'")
            
            for page in range(1, max_pages + 1):
                try:
                    # URL correcta según el usuario
                    url = f"{self.base_url}/co/trabajos/buscar/{term}"
                    if page > 1:
                        url += f"/pagina-{page}"
                    logger.info(f"Scrapeando página {page}: {url}")

                    response = self.session.get(url)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Extraer ofertas de la página
                    page_jobs = self._extract_jobs_from_page(soup)
                    
                    # Filtrar ofertas duplicadas por URL
                    new_jobs = []
                    for job in page_jobs:
                        job_url = job.get("url")
                        if job_url and job_url not in seen_urls:
                            seen_urls.add(job_url)
                            new_jobs.append(job)
                    
                    jobs.extend(new_jobs)

                    # Pausa entre requests para no ser bloqueado
                    time.sleep(2)

                    # Si no hay más ofertas en esta página, detener
                    if not page_jobs:
                        break

                except Exception as e:
                    logger.exception(f"Error en página {page} del término '{term}'")
                    break
            
            # Pausa entre términos para no ser bloqueado
            time.sleep(3)

        logger.info(f"✅ Scraping completado: {len(jobs)} ofertas únicas encontradas")
        return jobs

    def _extract_jobs_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrae las ofertas de una página específica"""
        jobs: List[Dict] = []
        seen_urls = set()

        # Tomar solo contenedores raíz de tarjeta para evitar duplicados por subcomponentes.
        job_cards = soup.find_all(
            "div",
            class_=lambda x: x and "magneto-ui-card-jobs_container" in x,
        )

        logger.debug(f"Encontradas {len(job_cards)} tarjetas raíz de ofertas")

        for card in job_cards:
            try:
                job_data = self._extract_job_data(card)
                if not job_data:
                    continue

                url = job_data.get("url")
                if not url or url in seen_urls:
                    continue

                seen_urls.add(url)
                if job_data.get('title'):
                    jobs.append(job_data)
            except Exception as e:
                logger.exception(f"Error extrayendo job en tarjeta {card}")
                continue

        return jobs

    def _extract_job_data(self, card) -> Optional[Dict]:
        """Extrae datos de una tarjeta de oferta individual"""
        try:
            # Extraer URL primero, para poder enriquecer desde la vista de detalle.
            url_elem = card.find('a', href=lambda x: x and '/co/empleos/' in x)
            url = url_elem['href'] if url_elem else None
            if url and not url.startswith('http'):
                url = self.base_url + url

            # Extraer título.
            title_elem = card.find(class_=lambda x: x and 'text--big' in x and 'text--bold' in x)
            title = title_elem.get_text().strip() if title_elem else None

            # Buscar empresa y tipo de contrato en los elementos de texto
            company = None
            remote_type = None
            text_elements = card.find_all(string=True, recursive=True)
            for text in text_elements:
                text = text.strip()
                # Buscar patrón "Empresa | Tipo contrato"
                if '|' in text and len(text.split('|')) >= 2:
                    parts = text.split('|', 1)
                    potential_company = parts[0].strip()
                    potential_contract = parts[1].strip()

                    # Verificar que no sea el título (que también puede tener |)
                    if potential_company != title:
                        company = potential_company
                        remote_type = potential_contract
                        break

            # Extraer ciudad/ubicación - buscar en elementos de texto
            city = None
            for text in text_elements:
                text = text.strip()
                # Buscar patrones de ciudad (ej: "Medellín", "Bogotá", etc.)
                if text == title:
                    continue
                if any(city_name in text for city_name in ['Medellín', 'Bogotá', 'Cali', 'Barranquilla', 'Cartagena', 'Bucaramanga', 'Pereira', 'Manizales', 'Ibagué', 'Cúcuta', 'Sabaneta', 'Guarne', 'Envigado', 'Itagui']):
                    city = text
                    break

            # Extraer salario si existe
            salary_text = None
            for text in text_elements:
                text = text.strip()
                if 'salario' in text.lower() or '$' in text or 'convenir' in text.lower():
                    salary_text = text
                    break

            # Parsear salario básico
            salary_min = salary_max = currency = None
            if salary_text and '$' in salary_text:
                numbers = re.findall(r"\d[\d\.]*", salary_text)
                if numbers:
                    salary_min = int(numbers[0].replace('.', ''))
                currency = 'COP'

            detail_data = self._extract_job_detail(url) if url else {}

            # Priorizar datos de detalle cuando estén disponibles.
            if detail_data.get("company"):
                company = detail_data["company"]
            if detail_data.get("remote_type"):
                remote_type = detail_data["remote_type"]
            if detail_data.get("city"):
                city = detail_data["city"]
            if detail_data.get("salary_min"):
                salary_min = detail_data["salary_min"]
            if detail_data.get("salary_max"):
                salary_max = detail_data["salary_max"]
            if detail_data.get("currency"):
                currency = detail_data["currency"]

            return {
                'source': 'magneto365',
                'title': title,
                'company': company,
                'city': city,
                'remote_type': remote_type,
                'url': url,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'currency': currency,
                'description': detail_data.get('description'),
                'skills': detail_data.get('skills'),
                'published_at': detail_data.get('published_at', datetime.now()),
                'scraped_at': datetime.now()
            }

        except Exception as e:
            logger.exception("Error extrayendo datos del job")
            return None

    def _extract_job_detail(self, url: str) -> Dict:
        """Extrae metadatos desde la página de detalle de una vacante."""
        try:
            response = self.session.get(url, timeout=20)
            if response.status_code >= 500:
                logger.warning(
                    f"Magneto devolvió HTTP {response.status_code} para detalle {url}; se omite enriquecimiento"
                )
                return {}
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Fecha de publicación: "Fecha de publicación YYYY-MM-DD"
            published_at = None
            publish_elem = soup.find(
                "span",
                class_=lambda x: x and "header_publish-date" in x,
            )
            if publish_elem:
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", publish_elem.get_text(" ", strip=True))
                if date_match:
                    published_at = datetime.strptime(date_match.group(1), "%Y-%m-%d")

            company = None
            company_elem = soup.find("a", class_=lambda x: x and "header__company" in x)
            if company_elem:
                company = company_elem.get_text(" ", strip=True)

            remote_type = None
            contract_elem = soup.find("span", class_=lambda x: x and "contract-type" in x)
            if contract_elem:
                remote_type = contract_elem.get_text(" ", strip=True).lstrip("| ").strip()

            city = None
            summary_labels = soup.find_all("span", class_=lambda x: x and "summary_label" in x)
            for label in summary_labels:
                txt = label.get_text(" ", strip=True)
                if any(city_name in txt for city_name in ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", "Bucaramanga", "Pereira", "Sabaneta", "Guarne"]):
                    city = txt
                    break

            salary_min = salary_max = None
            currency = None
            for label in summary_labels:
                txt = label.get_text(" ", strip=True)
                if "$" in txt:
                    numbers = re.findall(r"\d[\d\.]*", txt)
                    if numbers:
                        salary_min = int(numbers[0].replace('.', ''))
                        salary_max = salary_min
                        currency = "COP"
                    break

            description = None
            description_elem = soup.find("div", class_=lambda x: x and "JobOfferDetailContent_content" in x)
            if description_elem:
                description = description_elem.get_text("\n", strip=True)

            skills: List[str] = []
            skill_nodes = soup.find_all("span", class_=lambda x: x and "skill_name" in x)
            for node in skill_nodes:
                value = node.get_text(" ", strip=True)
                if value:
                    skills.append(value)

            return {
                "company": company,
                "remote_type": remote_type,
                "city": city,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "currency": currency,
                "description": description,
                "skills": skills or None,
                "published_at": published_at,
            }
        except RequestException as exc:
            logger.warning(f"No se pudo enriquecer detalle para URL {url}: {exc}")
            return {}
        except Exception:
            logger.exception(f"Error parseando detalle para URL: {url}")
            return {}