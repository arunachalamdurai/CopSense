"""CopSense — Configuration"""
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent

class Settings(BaseSettings):
    SECRET_KEY: str = "copsense-super-secret-key-bihar-police-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/copsense.db"
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    ENVIRONMENT: str = "development"

    model_config = {"env_file": BASE_DIR / ".env", "extra": "ignore"}

settings = Settings()
