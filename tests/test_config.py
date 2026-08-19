import unittest

from pensabot.config import (
    ConfigurationError,
    DatabaseConfig,
    TelegramConfig,
    load_database_config,
    load_telegram_config,
)


class LoadDatabaseConfigTests(unittest.TestCase):
    def test_loads_valid_configuration(self) -> None:
        config = load_database_config(
            {
                "DATABASE_URL": "postgresql://localhost/pensabot",
                "MEMORY_MAX_MESSAGES": "12",
                "MEMORY_SEARCH_LIMIT": "8",
            }
        )

        self.assertEqual(
            config,
            DatabaseConfig(
                url="postgresql://localhost/pensabot",
                recent_message_limit=12,
                memory_search_limit=8,
            ),
        )

    def test_defaults_recent_message_limit(self) -> None:
        config = load_database_config(
            {"DATABASE_URL": "postgresql://localhost/pensabot"}
        )

        self.assertEqual(config.recent_message_limit, 20)
        self.assertEqual(config.memory_search_limit, 10)

    def test_requires_database_url(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "DATABASE_URL"):
            load_database_config({})

    def test_rejects_non_positive_recent_message_limit(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "greater than zero"):
            load_database_config(
                {
                    "DATABASE_URL": "postgresql://localhost/pensabot",
                    "MEMORY_MAX_MESSAGES": "0",
                }
            )

    def test_rejects_non_positive_memory_search_limit(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "greater than zero"):
            load_database_config(
                {
                    "DATABASE_URL": "postgresql://localhost/pensabot",
                    "MEMORY_SEARCH_LIMIT": "0",
                }
            )

    def test_rejects_non_integer_memory_search_limit(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "must be an integer"):
            load_database_config(
                {
                    "DATABASE_URL": "postgresql://localhost/pensabot",
                    "MEMORY_SEARCH_LIMIT": "many",
                }
            )


class LoadTelegramConfigTests(unittest.TestCase):
    def test_loads_valid_configuration(self) -> None:
        config = load_telegram_config(
            {
                "TELEGRAM_API_KEY": "token",
                "ALLOWED_CHATS": "123, 456",
            }
        )

        self.assertEqual(
            config,
            TelegramConfig(api_key="token", allowed_chat_ids=frozenset({123, 456})),
        )

    def test_requires_api_key(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "TELEGRAM_API_KEY"):
            load_telegram_config({"ALLOWED_CHATS": "123"})

    def test_rejects_invalid_chat_ids(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "comma-separated integers"):
            load_telegram_config(
                {
                    "TELEGRAM_API_KEY": "token",
                    "ALLOWED_CHATS": "123,invalid",
                }
            )


if __name__ == "__main__":
    unittest.main()
