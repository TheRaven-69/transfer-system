import os
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_ENV: Literal["dev", "test", "k8s", "prod"] = "dev"

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "transfer_db"

    DATABASE_URL: str
    REDIS_URL: str
    RABBITMQ_URL: str

    CACHE_ENABLED: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    NOTIFY_FAIL_RATE: float = Field(default=0.0, ge=0.0, le=1.0)
    NOTIFY_DELAY_SEC: float = Field(default=2.0, ge=0.0)

    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        allowed_prefixes = (
            "postgresql://",
            "postgresql+psycopg://",
            "sqlite://",
            "sqlite+pysqlite://",
        )

        if not value.startswith(allowed_prefixes):
            raise ValueError(
                "DATABASE_URL must start with postgresql://, postgresql+psycopg://, "
                "sqlite:// or sqlite+pysqlite://"
            )

        return value

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        allowed_prefixes = ("redis://", "rediss://")

        if not value.startswith(allowed_prefixes):
            raise ValueError("REDIS_URL must start with redis:// or rediss://")

        return value

    @field_validator("RABBITMQ_URL")
    @classmethod
    def validate_rabbitmq_url(cls, value: str) -> str:
        allowed_prefixes = ("amqp://", "amqps://", "memory://")

        if not value.startswith(allowed_prefixes):
            raise ValueError(
                "RABBITMQ_URL must start with amqp://, amqps:// or memory://"
            )

        return value

    @field_validator("SENTRY_DSN", mode="before")
    @classmethod
    def empty_sentry_dsn_is_none(cls, v: str | None) -> str | None:
        if v == "":
            return None
        return v

    @field_validator("SENTRY_DSN")
    @classmethod
    def validate_sentry_dsn(cls, value: str | None) -> str | None:
        if value is None:
            return value

        if not value.startswith(("http://", "https://")):
            raise ValueError("SENTRY_DSN must start with http:// or https://")

        return value


settings = Settings()  # type: ignore[call-arg]
