import os
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE_OVERRIDE = os.getenv("PENSABOT_ENV_FILE")
ENV_FILES = (
    (ENV_FILE_OVERRIDE,)
    if ENV_FILE_OVERRIDE
    else (
        str(REPO_ROOT / ".env"),
    )
)


class Settings(BaseSettings):
    # Postgres (these vars are also used by the postgres Docker container)
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "pensabot"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # App
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    base_url: str = "http://localhost:8000"
    secret_key: str = "change-me-in-production"
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 512
    media_dir: str = "media"

    model_config = {"env_file": ENV_FILES, "extra": "ignore"}

    @computed_field
    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @computed_field
    @property
    def celery_database_url(self) -> str:
        return f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @computed_field
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"

    @computed_field
    @property
    def celery_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/1"


settings = Settings()
