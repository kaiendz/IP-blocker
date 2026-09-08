"""Application configuration, loaded from environment variables / .env."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    APP_NAME: str = "IP Blacklister"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg://blacklister:blacklister@localhost:5432/blacklister"

    # --- Auth / JWT ---
    SECRET_KEY: str = "CHANGE_ME_dev_only_secret_key_do_not_use_in_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Secret-at-rest encryption (Fernet key, 32 url-safe base64 bytes) ---
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FERNET_KEY: str = "5Z8U3vQvQpQmQK2E4dQZ0aQmQK2E4dQZ0aQmQK2E4dQ="

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:8080"]

    # --- Bootstrap admin (used only by seed script on first run) ---
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@example.com"
    BOOTSTRAP_ADMIN_PASSWORD: str = "ChangeMe123!"

    # --- Scheduler defaults (minutes unless noted) ---
    DEVICE_POLL_INTERVAL_MINUTES: int = 2
    DETECTION_INTERVAL_MINUTES: int = 2
    THREAT_INTEL_DEFAULT_REFRESH_MINUTES: int = 60
    EXPIRY_SWEEP_INTERVAL_MINUTES: int = 5
    AZURE_PUBLISH_INTERVAL_MINUTES: int = 5

    # --- Detection defaults (used to seed the default rule) ---
    DEFAULT_THRESHOLD_COUNT: int = 5
    DEFAULT_WINDOW_MINUTES: int = 10
    DEFAULT_TTL_HOURS: int = 24

    # --- Azure publish defaults ---
    DEFAULT_AZURE_CHUNK_SIZE: int = 2000
    DEFAULT_SAS_EXPIRY_DAYS: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
