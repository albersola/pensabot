from config import Settings


def test_database_url_constructed_from_parts():
    s = Settings(
        postgres_user="u",
        postgres_password="p",
        postgres_host="h",
        postgres_port=1234,
        postgres_db="db",
    )
    assert s.database_url == "postgresql+asyncpg://u:p@h:1234/db"


def test_celery_database_url_uses_psycopg():
    s = Settings(postgres_user="u", postgres_password="p", postgres_host="h", postgres_port=5432, postgres_db="db")
    assert s.celery_database_url == "postgresql+psycopg://u:p@h:5432/db"


def test_redis_url_constructed_from_parts():
    s = Settings(redis_host="r", redis_port=9999)
    assert s.redis_url == "redis://r:9999"


def test_celery_broker_url_uses_db_1():
    s = Settings(redis_host="r", redis_port=6379)
    assert s.celery_broker_url == "redis://r:6379/1"
