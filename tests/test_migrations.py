from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text

from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def alembic_config(database_url: str) -> Config:
    config = Config(PROJECT_ROOT / "alembic.ini")
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_migrations_upgrade_existing_schema_and_preserve_legacy_users():
    database_path = PROJECT_ROOT / f".migration-test-{uuid4().hex}.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    config = alembic_config(database_url)
    engine = None

    try:
        command.upgrade(config, "20260830_01")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO users (id) VALUES (7)"))

        command.upgrade(config, "head")

        inspector = inspect(engine)
        assert set(inspector.get_table_names()) >= {
            "users",
            "wallets",
            "transactions",
            "refresh_tokens",
            "alembic_version",
        }
        assert {column["name"] for column in inspector.get_columns("users")} >= {
            "username",
            "email",
            "password_hash",
        }
        with engine.connect() as connection:
            legacy_user = connection.execute(
                text("SELECT username, email, password_hash FROM users WHERE id = 7")
            ).one()
        assert legacy_user == ("legacy_7", "legacy_7@invalid.local", "disabled")

        command.downgrade(config, "base")
        assert inspect(engine).get_table_names() == ["alembic_version"]
    finally:
        if engine is not None:
            engine.dispose()
        database_path.unlink(missing_ok=True)
