import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
from datetime import datetime

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

    def get_jobs(self, search_term: str = "desarrollador", location: str = "colombia", max_pages: int = 3) -> List[Dict]:
        """
        Extrae ofertas de empleo de Magneto365

        Args:
            search_term: Término de búsqueda (ej: "desarrollador", "python")
            location: Ubicación (ej: "colombia", "bogota")
            max_pages: Número máximo de páginas a scrapear

        Returns:
            Lista de diccionarios con datos de las ofertas
        """
        jobs = []

        for page in range(1, max_pages + 1):
            try:
                # URL correcta según el usuario
                url = f"{self.base_url}/co/trabajos/buscar/{search_term}"
                if page > 1:
                    url += f"?page={page}"
                logger.info(f"Scrapeando página {page}: {url}")

                response = self.session.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # Extraer ofertas de la página
                page_jobs = self._extract_jobs_from_page(soup)
                jobs.extend(page_jobs)

                # Pausa entre requests para no ser bloqueado
                time.sleep(2)

                # Si no hay más ofertas en esta página, detener
                if not page_jobs:
                    break

            except Exception as e:
                logger.exception(f"Error en página {page}")
                break

        return jobs

    def _extract_jobs_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrae las ofertas de una página específica"""
        jobs = []

        # Selector para tarjetas de ofertas basado en la inspección
        # Buscar elementos con clase que contenga 'job_card' o 'card-jobs'
        job_cards = soup.find_all('div', class_=lambda x: x and ('job_card' in x or 'card-jobs' in x or 'mg_job_card' in x))

        logger.debug(f"Encontradas {len(job_cards)} tarjetas de ofertas")

        for card in job_cards:
            try:
                job_data = self._extract_job_data(card)
                if job_data and job_data.get('title'):  # Solo si tiene título
                    jobs.append(job_data)
            except Exception as e:
                logger.exception(f"Error extrayendo job en tarjeta {card}")
                continue

        return jobs

    def _extract_job_data(self, card) -> Optional[Dict]:
        """Extrae datos de una tarjeta de oferta individual"""
        try:
            # Extraer título - buscar elementos con clase específica
            title_elem = card.find(class_=lambda x: x and 'text--big' in x and 'text--bold' in x)
            title = title_elem.get_text().strip() if title_elem else None

            # Buscar empresa y tipo de contrato en los elementos de texto
            company = None
            remote_type = None
            text_elements = card.find_all(text=True, recursive=True)
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
            text_elements = card.find_all(text=True, recursive=True)
            for text in text_elements:
                text = text.strip()
                # Buscar patrones de ciudad (ej: "Medellín", "Bogotá", etc.)
                if any(city_name in text for city_name in ['Medellín', 'Bogotá', 'Cali', 'Barranquilla', 'Cartagena', 'Bucaramanga', 'Pereira', 'Manizales', 'Ibagué', 'Cúcuta']):
                    city = text
                    break

            # Extraer URL - buscar enlaces
            url_elem = card.find('a', href=lambda x: x and 'empleos' in x)
            url = url_elem['href'] if url_elem else None
            if url and not url.startswith('http'):
                url = self.base_url + url

            # Extraer salario si existe
            salary_text = None
            for text in text_elements:
                text = text.strip()
                if 'salario' in text.lower() or '$' in text or 'convenir' in text.lower():
                    salary_text = text
                    break

            # Parsear salario básico (placeholder)
            salary_min = salary_max = currency = None
            if salary_text and '$' in salary_text:
                # Aquí podríamos implementar parsing más sofisticado
                currency = 'COP'

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
                'published_at': datetime.now(),  # Placeholder
                'scraped_at': datetime.now()
            }

        except Exception as e:
            logger.exception("Error extrayendo datos del job")
            return None