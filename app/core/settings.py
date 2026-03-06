from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",  # якщо .env немає — ок
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # env mode
    APP_ENV: str = Field(default="dev")

    # canonical (new)
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None
    RABBITMQ_URL: str | None = None

    CACHE_ENABLED: bool = Field(default=False)

    NOTIFY_FAIL_RATE: float = Field(default=0.0, ge=0.0, le=1.0)
    NOTIFY_DELAY_SEC: float = Field(default=2.0, ge=0.0)

    # backward compat (temporary for PR1)
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    def finalize(self) -> "Settings":
        # compat mapping
        if self.RABBITMQ_URL is None and self.CELERY_BROKER_URL:
            self.RABBITMQ_URL = self.CELERY_BROKER_URL

        if self.REDIS_URL is None and self.CELERY_RESULT_BACKEND:
            self.REDIS_URL = self.CELERY_RESULT_BACKEND

        # dev defaults (local/tests)
        if self.APP_ENV.lower() == "dev":
            if self.DATABASE_URL is None:
                self.DATABASE_URL = "sqlite+pysqlite:///./app.db"
            if self.REDIS_URL is None:
                self.REDIS_URL = "redis://localhost:6379/0"
            if self.RABBITMQ_URL is None:
                self.RABBITMQ_URL = "amqp://guest:guest@rabbitmq:5672//"

        # prod fail-fast
        if self.APP_ENV.lower() != "dev":
            missing = [
                k
                for k in ("DATABASE_URL", "REDIS_URL", "RABBITMQ_URL")
                if getattr(self, k) in (None, "")
            ]
            if missing:
                raise ValueError(
                    f"Missing required settings for APP_ENV={self.APP_ENV}: {', '.join(missing)}"
                )

        return self


settings = Settings().finalize()