import os
from typing import Literal

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "dev", "test", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_ENV: Environment = "dev"

    DATABASE_URL: str
    REDIS_URL: str
    RABBITMQ_URL: str

    CACHE_ENABLED: bool = False
    LOG_LEVEL: str = "INFO"

    NOTIFY_FAIL_RATE: float = Field(default=0.0, ge=0.0, le=1.0)
    NOTIFY_DELAY_SEC: float = Field(default=2.0, ge=0.0)

    SENTRY_DSN: AnyUrl | None = None
    SENTRY_ENVIRONMENT: Environment | None = None
    SENTRY_RELEASE: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.0, ge=0.0, le=1.0)
    SENTRY_PROFILES_SAMPLE_RATE: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator(
        "SENTRY_DSN", "SENTRY_ENVIRONMENT", "SENTRY_RELEASE", mode="before"
    )
    @classmethod
    def empty_string_as_none(cls, value):
        if value == "":
            return None
        return value


settings = Settings()
