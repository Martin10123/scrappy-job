import sys
from loguru import logger

logger.add(
    "logs/jobtrend.log",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    level="INFO",
    backtrace=True,
    diagnose=True,
)

# Ajustes generales del logger
logger.configure(
    handlers=[
        {"sink": sys.stdout, "level": "INFO", "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"},
        {"sink": "logs/jobtrend.log", "level": "DEBUG", "rotation": "10 MB", "retention": "7 days", "compression": "zip"},
    ]
)

__all__ = ["logger"]
