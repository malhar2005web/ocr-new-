import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_STORAGE = str((BASE_DIR / "storage" / "uploads").resolve())

class Settings(BaseSettings):
    APP_NAME: str = "PCS Universal Document Intelligence"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Storage: Absolute path within workspace
    STORAGE_DIR: str = DEFAULT_STORAGE

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ocr_db"

    # OCR configuration
    TESSERACT_CMD: Optional[str] = None

    # LLM configuration (free tier: Google Gemini 1.5 Flash recommended)
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-3.8-flash"
    LLM_API_KEY: Optional[str] = None

    # Verification threshold
    MAX_RECOVERY_ATTEMPTS: int = 2

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()

# Ensure absolute storage directory exists safely
try:
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
except Exception:
    pass
