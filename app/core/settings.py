import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_ENV: str = "dev"
    DATABASE_URL: str
    REDIS_URL: str
    RABBITMQ_URL: str

    CACHE_ENABLED: bool = False
    LOG_LEVEL: str = "INFO"

    NOTIFY_FAIL_RATE: float = Field(default=0.0, ge=0.0, le=1.0)
    NOTIFY_DELAY_SEC: float = Field(default=2.0, ge=0.0)


settings = Settings()
