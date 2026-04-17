import re
import time
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.logger import logger


class ComputrabajoScraper:
    """Scraper para Computrabajo Colombia."""

    def __init__(self):
        self.base_url = "https://co.computrabajo.com"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }
        )

    def get_jobs(
        self,
        search_term: str = "desarrollador",
        location: str = "colombia",
        max_pages: int = 5,
    ) -> List[Dict]:
        """Extrae ofertas de Computrabajo por búsqueda y ubicación."""
        jobs: List[Dict] = []
        max_pages = max(max_pages, 1)
        seen_urls = set()

        for page in range(1, max_pages + 1):
            url = self._build_search_url(search_term=search_term, location=location, page=page)
            logger.info(f"Scrapeando Computrabajo página {page}: {url}")

            try:
                response = self.session.get(url, timeout=20)
                response.raise_for_status()
            except Exception:
                logger.exception(f"No se pudo consultar la página {page} de Computrabajo")
                break

            soup = BeautifulSoup(response.content, "html.parser")
            offer_urls = self._extract_offer_urls_from_search(soup)
            logger.info(f"Computrabajo página {page}: {len(offer_urls)} URLs de ofertas encontradas")

            if not offer_urls:
                break

            for offer_url in offer_urls:
                if offer_url in seen_urls:
                    continue

                seen_urls.add(offer_url)
                detail = self._extract_job_detail(offer_url)
                if detail and detail.get("title"):
                    jobs.append(detail)

                # Pausa corta para reducir probabilidad de bloqueo.
                time.sleep(1)

            # Pausa entre páginas.
            time.sleep(1)

        return jobs

    def _build_search_url(self, search_term: str, location: str, page: int) -> str:
        term_slug = self._slugify(search_term)
        location_slug = self._slugify(location)

        base_path = f"/trabajo-de-{term_slug}-en-{location_slug}"
        if page == 1:
            return f"{self.base_url}{base_path}"
        return f"{self.base_url}{base_path}?p={page}"

    def _slugify(self, value: str) -> str:
        value = value.lower().strip()
        value = unicodedata.normalize("NFD", value)
        value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
        value = re.sub(r"[^a-z0-9]+", "-", value)
        value = re.sub(r"-+", "-", value).strip("-")
        return value or "colombia"

    def _extract_offer_urls_from_search(self, soup: BeautifulSoup) -> List[str]:
        urls: List[str] = []
        seen = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "")
            if "/ofertas-de-trabajo/oferta-de-trabajo-" not in href:
                continue

            abs_url = urljoin(self.base_url, href)
            if abs_url not in seen:
                seen.add(abs_url)
                urls.append(abs_url)

        return urls

    def _extract_job_detail(self, url: str) -> Optional[Dict]:
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            container = soup.find(attrs={"data-offers-grid-detail-container": True}) or soup

            title = self._extract_title(container)
            company = self._extract_company(container)
            city = self._extract_city(container)
            description = self._extract_description(container)

            details = self._extract_offer_detail_lines(container)
            salary_min, salary_max, currency = self._parse_salary(details)
            remote_type = self._extract_remote_type(details)

            listed_skills = self._extract_skills_from_requirements(container)
            nlp_skills = self._extract_skills_from_text(description)
            skills = sorted(set(listed_skills + nlp_skills)) or None

            published_at = self._extract_published_date(container) or datetime.now()

            return {
                "source": "computrabajo",
                "title": title,
                "company": company,
                "city": city,
                "remote_type": remote_type,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "currency": currency,
                "description": description,
                "skills": skills,
                "url": url,
                "published_at": published_at,
                "scraped_at": datetime.now(),
            }
        except Exception:
            logger.exception(f"Error extrayendo detalle de Computrabajo URL: {url}")
            return None

    def _extract_title(self, container: BeautifulSoup) -> Optional[str]:
        title_node = container.find(attrs={"data-offers-grid-detail-title": True})
        if not title_node:
            title_node = container.find("h1")
        if not title_node:
            return None
        value = title_node.get_text(" ", strip=True)
        return value or None

    def _extract_company(self, container: BeautifulSoup) -> Optional[str]:
        header = container.find("div", class_="header_detail")
        if header:
            company_link = header.find("a", href=True)
            if company_link:
                value = company_link.get_text(" ", strip=True)
                if value:
                    return value

        fallback = container.find(attrs={"offer-detail-not-applied": True})
        if fallback:
            value = fallback.get_text(" ", strip=True)
            if value:
                return value

        return None

    def _extract_city(self, container: BeautifulSoup) -> Optional[str]:
        header = container.find("div", class_="header_detail")
        if header:
            for p_node in header.find_all("p"):
                text = p_node.get_text(" ", strip=True)
                if "," in text and len(text) > 3:
                    return text
        return None

    def _extract_description(self, container: BeautifulSoup) -> Optional[str]:
        desc_wrapper = container.find(attrs={"description-offer": True})
        if not desc_wrapper:
            return None

        text_node = desc_wrapper.find("div", class_=lambda x: x and "t_word_wrap" in x)
        if not text_node:
            text_node = desc_wrapper

        text = text_node.get_text("\n", strip=True)
        return text or None

    def _extract_offer_detail_lines(self, container: BeautifulSoup) -> List[str]:
        lines: List[str] = []
        description = container.find(attrs={"description-offer": True})
        if not description:
            return lines

        for p_node in description.find_all("p", class_=lambda x: x and "dFlex" in x):
            line = p_node.get_text(" ", strip=True)
            if line:
                lines.append(line)

        return lines

    def _parse_salary(self, detail_lines: List[str]) -> tuple[Optional[int], Optional[int], Optional[str]]:
        for line in detail_lines:
            if "$" not in line:
                continue

            # Captura montos como 5.200.000,00 y los normaliza a entero COP.
            values = re.findall(r"\$\s*([\d\.]+)(?:,\d+)?", line)
            if not values:
                continue

            amounts = [int(v.replace(".", "")) for v in values]
            salary_min = min(amounts)
            salary_max = max(amounts)
            return salary_min, salary_max, "COP"

        return None, None, None

    def _extract_remote_type(self, detail_lines: List[str]) -> Optional[str]:
        options = {
            "presencial": "presencial",
            "remoto": "remoto",
            "hibrido": "hibrido",
            "híbrido": "hibrido",
            "teletrabajo": "remoto",
        }

        for line in detail_lines:
            lowered = line.lower()
            for key, normalized in options.items():
                if key in lowered:
                    return normalized

        return None

    def _extract_skills_from_requirements(self, container: BeautifulSoup) -> List[str]:
        description = container.find(attrs={"description-offer": True})
        if not description:
            return []

        for li_node in description.find_all("li"):
            text = li_node.get_text(" ", strip=True)
            if not text.lower().startswith("conocimientos:"):
                continue

            skills_raw = text.split(":", 1)[-1]
            return [
                skill.strip().lower()
                for skill in skills_raw.split(",")
                if skill.strip()
            ]

        return []

    def _extract_skills_from_text(self, text: Optional[str]) -> List[str]:
        if not text:
            return []

        # Diccionario simple para MVP.
        known_skills = [
            "python",
            "django",
            "flask",
            "fastapi",
            "javascript",
            "typescript",
            "react",
            "vue",
            "angular",
            "node",
            "node.js",
            "html",
            "css",
            "sass",
            "less",
            "docker",
            "kubernetes",
            "aws",
            "azure",
            "gcp",
            "postgresql",
            "mysql",
            "mongodb",
            "linux",
            "git",
            "vtex",
            "gtm",
        ]

        lowered = text.lower()
        found = []
        for skill in known_skills:
            pattern = rf"\b{re.escape(skill)}\b"
            if re.search(pattern, lowered):
                found.append(skill.replace("node.js", "nodejs"))
        return found

    def _extract_published_date(self, container: BeautifulSoup) -> Optional[datetime]:
        text = container.get_text(" ", strip=True)

        # Ejemplos comunes: "Publicado el 12 de marzo", "Hace 3 días".
        date_match = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)", text.lower())
        if not date_match:
            return None

        day = int(date_match.group(1))
        month_name = date_match.group(2)
        months = {
            "enero": 1,
            "febrero": 2,
            "marzo": 3,
            "abril": 4,
            "mayo": 5,
            "junio": 6,
            "julio": 7,
            "agosto": 8,
            "septiembre": 9,
            "setiembre": 9,
            "octubre": 10,
            "noviembre": 11,
            "diciembre": 12,
        }
        month = months.get(month_name)
        if not month:
            return None

        now = datetime.now()
        try:
            return datetime(year=now.year, month=month, day=day)
        except ValueError:
            return None