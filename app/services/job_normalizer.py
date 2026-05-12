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

_DISPLAY_SKILL_ALIASES = {
    "trabajoenequipo": "Trabajo en equipo",
    "comunicacionefectiva": "Comunicacion efectiva",
    "comunicacinefectiva": "Comunicacion efectiva",
    "resolucindeproblemas": "Resolucion de problemas",
    "pensamientoanalitico": "Pensamiento analitico",
    "aprendizajecontinuo": "Aprendizaje continuo",
    "liderazgo": "Liderazgo",
    "proactividad": "Proactividad",
    "adaptacion": "Adaptacion",
    "apirest": "API REST",
    "nodejs": "Node.js",
    "reactjs": "React.js",
    "net": ".NET",
}

_SOFT_SKILL_KEYS = {
    "trabajoenequipo",
    "comunicacionefectiva",
    "comunicacinefectiva",
    "resolucindeproblemas",
    "pensamientoanalitico",
    "aprendizajecontinuo",
    "liderazgo",
    "proactividad",
    "adaptacion",
    "adaptabilidad",
    "colaboracion",
    "comunicacion",
    "disciplina",
    "orientacionallogro",
    "orientacionalresultado",
    "pensamientocritico",
    "trabajoenequipo",
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

    raw = skill.strip()
    if not raw:
        return ""

    # Conserva separacion de camelCase (ej: trabajoEnEquipo) antes de normalizar.
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw)
    clean = _strip_accents(camel_spaced).lower()

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


def denormalize_skill(skill: str) -> str:
    """Convierte un skill normalizado (camelCase) a formato legible con espacios.
    
    Ejemplos:
        trabajoEnEquipo -> Trabajo en equipo
        javascript -> Javascript
        apiRest -> Api Rest
    """
    if not isinstance(skill, str) or not skill:
        return skill

    compact_key = re.sub(r"[^a-z0-9]+", "", _strip_accents(skill).lower())
    if compact_key in _DISPLAY_SKILL_ALIASES:
        return _DISPLAY_SKILL_ALIASES[compact_key]
    
    # Buscar el skill en los aliases para obtener el nombre original
    for original, normalized in _SKILL_ALIASES.items():
        if normalized == skill:
            words = original.split()
            if not words:
                return skill
            return words[0].capitalize() + (" " + " ".join(word.lower() for word in words[1:]) if len(words) > 1 else "")
    
    # Si no esta en aliases, convertir camelCase a formato legible.
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', skill)
    words = result.split()
    if not words:
        return skill
    return words[0].capitalize() + (" " + " ".join(word.lower() for word in words[1:]) if len(words) > 1 else "")


def format_skill(skill: object) -> str:
    normalized_skill = normalize_skill(skill)
    if not normalized_skill:
        return ""
    return denormalize_skill(normalized_skill)


def is_soft_skill(skill: object) -> bool:
    normalized_skill = normalize_skill(skill)
    if not normalized_skill:
        return False

    compact_key = re.sub(r"[^a-z0-9]+", "", _strip_accents(normalized_skill).lower())
    return compact_key in _SOFT_SKILL_KEYS


def skill_category(skill: object) -> str:
    return "soft" if is_soft_skill(skill) else "technical"


def detect_english_requirement(*texts: Optional[str]) -> Optional[bool]:
    combined_texts = [text for text in texts if isinstance(text, str) and text.strip()]
    if not combined_texts:
        return None

    normalized_text = _strip_accents(" ".join(combined_texts).lower())
    normalized_text = re.sub(r"\s+", " ", normalized_text)

    negative_patterns = [
        r"no requiere ingles",
        r"sin ingles",
        r"ingles no requerido",
        r"not required in english",
        r"english not required",
    ]
    positive_patterns = [
        r"requiere.*ingles",
        r"postular en ingles",
        r"ingles.*requerid",
        r"english required",
        r"must be.*english",
        r"fluent in english",
        r"intermediate english",
        r"advanced english",
        r"b2 english",
        r"english level",
    ]

    for pattern in negative_patterns:
        if re.search(pattern, normalized_text):
            return False

    for pattern in positive_patterns:
        if re.search(pattern, normalized_text):
            return True

    if re.search(r"\bingles\b|\benglish\b", normalized_text):
        return True

    return None


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
