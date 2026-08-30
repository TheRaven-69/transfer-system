import os
from logging.config import fileConfig

from dotenv import dotenv_values
from sqlalchemy import engine_from_config, pool

from alembic import context
from app.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def _database_url() -> str:
    env_file = os.getenv("ENV_FILE", ".env")
    file_values = dotenv_values(env_file)
    url = (
        os.getenv("DATABASE_URL")
        or config.get_main_option("sqlalchemy.url")
        or file_values.get("DATABASE_URL")
    )
    if not url:
        raise RuntimeError(
            "DATABASE_URL must be set in the environment, ENV_FILE, or alembic.ini"
        )
    return str(url)


config.set_main_option("sqlalchemy.url", _database_url().replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
