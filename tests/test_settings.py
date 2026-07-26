import pytest
from pydantic import ValidationError

from app.core.settings import Settings


def make_settings(**overrides):
    data = {
        "APP_ENV": "dev",
        "DATABASE_URL": "postgresql+psycopg://postgres:postgres@db:5432/transfer_db",
        "REDIS_URL": "redis://redis:6379/0",
        "RABBITMQ_URL": "amqp://guest:guest@rabbitmq:5672//",
        "CACHE_ENABLED": "true",
        "LOG_LEVEL": "INFO",
        "NOTIFY_FAIL_RATE": "0.0",
        "NOTIFY_DELAY_SEC": "2.0",
        "sentry": {"dsn": "", "traces_sample_rate": "0.0"},
    }
    data.update(overrides)
    return Settings(**data)


def test_valid_settings():
    settings = make_settings()

    assert settings.APP_ENV == "dev"
    assert str(settings.REDIS_URL).startswith("redis://")
    assert str(settings.RABBITMQ_URL).startswith("amqp://")
    assert settings.CACHE_ENABLED is True
    assert settings.LOG_LEVEL == "INFO"


def test_invalid_log_level_fails_fast():
    with pytest.raises(ValidationError):
        make_settings(LOG_LEVEL="banana")


def test_invalid_app_env_fails_fast():
    with pytest.raises(ValidationError):
        make_settings(APP_ENV="productionnn")


def test_invalid_notify_fail_rate_fails_fast():
    with pytest.raises(ValidationError):
        make_settings(NOTIFY_FAIL_RATE="2.0")


def test_invalid_notify_delay_fails_fast():
    with pytest.raises(ValidationError):
        make_settings(NOTIFY_DELAY_SEC="-0.1")


def test_invalid_database_url_fails_fast():
    with pytest.raises(ValidationError):
        make_settings(DATABASE_URL="mysql://db/transfer_db")


def test_invalid_redis_url_fails_fast():
    with pytest.raises(ValidationError):
        make_settings(REDIS_URL="not-a-url")


def test_invalid_redis_scheme_fails_fast():
    with pytest.raises(ValidationError):
        make_settings(REDIS_URL="http://redis:6379/0")


def test_invalid_rabbitmq_url_fails_fast():
    with pytest.raises(ValidationError):
        make_settings(RABBITMQ_URL="redis://rabbitmq:5672//")


def test_invalid_sentry_dsn_fails_fast():
    with pytest.raises(ValidationError):
        make_settings(sentry={"dsn": "banana"})


def test_non_http_sentry_dsn_fails_fast():
    with pytest.raises(ValidationError):
        make_settings(sentry={"dsn": "ftp://example.com/project"})


@pytest.mark.parametrize("field", ["traces_sample_rate", "profiles_sample_rate"])
def test_invalid_sentry_sample_rate_fails_fast(field):
    with pytest.raises(ValidationError):
        make_settings(sentry={field: 1.1})


def test_empty_sentry_dsn_becomes_none():
    settings = make_settings(sentry={"dsn": ""})

    assert settings.sentry.dsn is None


def test_sqlite_database_url_allowed_for_tests():
    settings = make_settings(DATABASE_URL="sqlite+pysqlite:///:memory:")

    assert settings.DATABASE_URL == "sqlite+pysqlite:///:memory:"


@pytest.mark.parametrize("field", ["DATABASE_URL", "REDIS_URL", "RABBITMQ_URL"])
def test_critical_urls_are_required(field):
    data = {
        "APP_ENV": "test",
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/0",
        "RABBITMQ_URL": "memory://",
    }
    data.pop(field)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **data)
