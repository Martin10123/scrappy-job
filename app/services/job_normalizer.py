import re
from typing import List, Optional, Sequence
import unicodedata

_SKILL_ALIASES = {
    "api integration": "apiIntegration",
    "apis rest": "apiRest",
    "application security": "applicationSecurity",
    "artificial intelligence": "artificialIntelligence",
    "cloud services": "cloudServices",
    "cross platform development": "crossPlatformDevelopment",
    "data modeling": "dataModeling",
    "full stack": "fullStack",
    "github": "github",
    "google maps": "googleMaps",
    "jetpack compose": "jetpackCompose",
    "kubernetes": "kubernetes",
    "laravel": "laravel",
    "microservices": "microservices",
    "mobx": "mobx",
    "mvp": "mvp",
    "ngrx": "ngrx",
    "node js": "nodeJs",
    "nodejs": "nodeJs",
    "offline first": "offlineFirst",
    "openai api": "openAiApi",
    "postgresql": "postgresql",
    "power bi": "powerBi",
    "product management": "productManagement",
    "react native": "reactNative",
    "rest api": "restApi",
    "rpa": "rpa",
    "rxjs": "rxjs",
    "scrum": "scrum",
    "sql": "sql",
    "state management": "stateManagement",
    "ui ux implementation": "uiUxImplementation",
    "websocket": "webSocket",
    "web sockets": "webSocket",
    "workmanager": "workManager",
    "xcode": "xcode",
}

_REMOTE_KEYWORDS = {
    "remote": "remote",
    "remoto": "remote",
    "teletrabajo": "remote",
    "hybrid": "hybrid",
    "hibrido": "hybrid",
    "híbrido": "hybrid",
    "presencial": "onsite",
    "onsite": "onsite",
    "office": "onsite",
}

_KNOWN_CITIES = [
    # Colombia
    "Bogotá",
    "Medellín",
    "Cali",
    "Barranquilla",
    "Cartagena",
    "Bucaramanga",
    "Pereira",
    "Manizales",
    "Ibagué",
    "Cúcuta",
    "Villavicencio",
    "Pasto",
    "Montería",
    "Neiva",
    "Armenia",
    "Popayán",
    "Valledupar",
    "Santa Marta",
    "Sincelejo",
    "Tunja",
    "Sabaneta",
    "Envigado",
    "Itagüí",
    "Bello",
    "Rionegro",
    "Guarne",
    "Cereté",
    # Chile
    "Santiago",
    "Valparaíso",
    "Concepción",
    "La Serena",
    "Antofagasta",
    "Temuco",
    "Rancagua",
    "Talca",
    "Arica",
    "Puerto Montt",
    "Iquique",
    # Argentina
    "Buenos Aires",
    "Córdoba",
    "Rosario",
    "Mendoza",
    "La Plata",
    "Mar del Plata",
    "Tucumán",
    "Salta",
    "Santa Fe",
    "San Juan",
    # México
    "Ciudad de México",
    "Mexico City",
    "Guadalajara",
    "Monterrey",
    "Puebla",
    "Tijuana",
    "León",
    "Juárez",
    "Mérida",
    "Querétaro",
    "Zapopan",
    # Perú
    "Lima",
    "Arequipa",
    "Trujillo",
    "Chiclayo",
    "Cusco",
    "Piura",
    # Ecuador
    "Quito",
    "Guayaquil",
    "Cuenca",
    "Ambato",
    # Venezuela
    "Caracas",
    "Maracaibo",
    "Valencia",
    "Barquisimeto",
    # Uruguay
    "Montevideo",
    "Salto",
    "Paysandú",
    # Paraguay
    "Asunción",
    "Ciudad del Este",
    # Bolivia
    "La Paz",
    "Cochabamba",
    "Santa Cruz de la Sierra",
    # Costa Rica
    "San José",
    # Panamá
    "Ciudad de Panamá",
    # Guatemala
    "Ciudad de Guatemala",
    # España
    "Madrid",
    "Barcelona",
    "Valencia",
    "Sevilla",
    "Bilbao",
    "Málaga",
    "Zaragoza",
    # USA (remoto desde LATAM)
    "Miami",
    "New York",
    "Austin",
    "San Francisco",
]


def normalize_skills(skills: object) -> List[str]:
    if not isinstance(skills, Sequence) or isinstance(skills, (str, bytes)):
        return []

    normalized: List[str] = []
    seen = set()
    for skill in skills:
        normalized_skill = normalize_skill(skill)
        if not normalized_skill or normalized_skill in seen:
            continue
        seen.add(normalized_skill)
        normalized.append(normalized_skill)
    return normalized


def normalize_skill(skill: object) -> str:
    if not isinstance(skill, str):
        return ""

    clean = skill.strip().lower()
    if not clean:
        return ""

    alias_key = re.sub(r"[^a-z0-9]+", " ", clean)
    alias_key = re.sub(r"\s+", " ", alias_key).strip()
    if alias_key in _SKILL_ALIASES:
        return _SKILL_ALIASES[alias_key]

    parts = [part for part in re.split(r"[^a-z0-9]+", clean) if part]
    if not parts:
        return ""

    first = parts[0]
    rest = [part[:1].upper() + part[1:] for part in parts[1:]]
    return first + "".join(rest)


def detect_work_mode(city: Optional[str], contract_type: Optional[str]) -> Optional[str]:
    for text in (city, contract_type):
        if not isinstance(text, str):
            continue

        lowered = text.lower()
        for keyword, work_mode in _REMOTE_KEYWORDS.items():
            if keyword in lowered:
                return work_mode

    return None


def normalize_location_text(location_text: Optional[str]) -> Optional[str]:
    if not isinstance(location_text, str):
        return None

    cleaned = re.sub(r"\s+", " ", location_text.replace("\r", " ").replace("\n", " "))
    cleaned = cleaned.strip()
    return cleaned or None

def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

def extract_city_from_location(location_text: Optional[str]) -> Optional[str]:
    cleaned = normalize_location_text(location_text)
    if not cleaned:
        return None

    lowered = _strip_accents(cleaned.lower())

    # Primero descartar si es remoto
    if any(keyword in lowered for keyword in _REMOTE_KEYWORDS):
        return None

    # Buscar ciudad conocida con matching flexible (sin tildes)
    for city in _KNOWN_CITIES:
        if _strip_accents(city.lower()) in lowered:
            return city  # devuelve el nombre canónico limpio

    # Fallback: tomar lo que hay antes de la coma
    if "," in cleaned:
        return cleaned.split(",", 1)[0].strip() or None

    return cleaned
