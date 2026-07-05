import json
import os
from typing import Annotated, Literal

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["local", "dev", "test", "staging", "production"]
DEFAULT_SENTRY_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "idempotency-key",
        "idempotency_key",
    }
)


class SentrySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        env_prefix="SENTRY_",
        extra="ignore",
        case_sensitive=False,
    )

    dsn: AnyUrl | None = None
    environment: Environment | None = None
    release: str | None = None
    traces_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    profiles_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    sensitive_keys: Annotated[set[str], NoDecode] = Field(
        default_factory=lambda: set(DEFAULT_SENTRY_SENSITIVE_KEYS)
    )
    extra_sensitive_keys: Annotated[set[str], NoDecode] = Field(default_factory=set)

    @field_validator("dsn", "environment", "release", mode="before")
    @classmethod
    def empty_string_as_none(cls, value):
        if value == "":
            return None
        return value

    @field_validator("sensitive_keys", "extra_sensitive_keys", mode="before")
    @classmethod
    def parse_sensitive_keys(cls, value):
        if value is None:
            return set()
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return {key.strip() for key in value.split(",") if key.strip()}
        return value

    @field_validator("sensitive_keys", "extra_sensitive_keys", mode="after")
    @classmethod
    def normalize_sensitive_keys(cls, value):
        return {str(key).lower() for key in value}

    @property
    def all_sensitive_keys(self) -> set[str]:
        return self.sensitive_keys | self.extra_sensitive_keys


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

    sentry: SentrySettings = Field(default_factory=SentrySettings)


settings = Settings()  # type: ignore[call-arg]
