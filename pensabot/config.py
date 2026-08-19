import os
from collections.abc import Mapping
from dataclasses import dataclass


class ConfigurationError(ValueError):
    """Raised when required application configuration is invalid."""


@dataclass(frozen=True)
class TelegramConfig:
    api_key: str
    allowed_chat_ids: frozenset[int]


@dataclass(frozen=True)
class DatabaseConfig:
    url: str
    recent_message_limit: int
    memory_search_limit: int


def load_database_config(
    environment: Mapping[str, str] | None = None,
) -> DatabaseConfig:
    values = os.environ if environment is None else environment
    url = values.get("DATABASE_URL", "").strip()
    if not url:
        raise ConfigurationError("DATABASE_URL must be set")

    raw_recent_message_limit = values.get("MEMORY_MAX_MESSAGES", "20").strip()
    try:
        recent_message_limit = int(raw_recent_message_limit)
    except ValueError as error:
        raise ConfigurationError("MEMORY_MAX_MESSAGES must be an integer") from error

    if recent_message_limit <= 0:
        raise ConfigurationError("MEMORY_MAX_MESSAGES must be greater than zero")

    raw_memory_search_limit = values.get("MEMORY_SEARCH_LIMIT", "10").strip()
    try:
        memory_search_limit = int(raw_memory_search_limit)
    except ValueError as error:
        raise ConfigurationError("MEMORY_SEARCH_LIMIT must be an integer") from error

    if memory_search_limit <= 0:
        raise ConfigurationError("MEMORY_SEARCH_LIMIT must be greater than zero")

    return DatabaseConfig(
        url=url,
        recent_message_limit=recent_message_limit,
        memory_search_limit=memory_search_limit,
    )


def load_telegram_config(
    environment: Mapping[str, str] | None = None,
) -> TelegramConfig:
    values = os.environ if environment is None else environment
    api_key = values.get("TELEGRAM_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError("TELEGRAM_API_KEY must be set")

    raw_chat_ids = values.get("ALLOWED_CHATS", "")
    chat_id_values = [
        value.strip() for value in raw_chat_ids.split(",") if value.strip()
    ]
    if not chat_id_values:
        raise ConfigurationError("ALLOWED_CHATS must contain at least one chat ID")

    try:
        allowed_chat_ids = frozenset(int(value) for value in chat_id_values)
    except ValueError as error:
        raise ConfigurationError("ALLOWED_CHATS must contain comma-separated integers") from error

    return TelegramConfig(api_key=api_key, allowed_chat_ids=allowed_chat_ids)
