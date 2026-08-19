import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from pensabot.models import Memory
from pensabot.storage.memories import Memories


class SearchMemoriesTests(unittest.IsolatedAsyncioTestCase):
    async def test_searches_current_user_and_returns_memories(self) -> None:
        created_at = datetime(2026, 1, 1, tzinfo=UTC)
        updated_at = datetime(2026, 2, 1, tzinfo=UTC)
        row = (
            12,
            "telegram:456",
            "project.pensabot",
            "Pensabot uses PostgreSQL for durable memories.",
            "telegram:123",
            created_at,
            updated_at,
        )
        database = MagicMock()
        connection = AsyncMock()
        cursor = AsyncMock()
        database.connection.return_value.__aenter__ = AsyncMock(
            return_value=connection
        )
        database.connection.return_value.__aexit__ = AsyncMock(return_value=None)
        connection.execute.return_value = cursor
        cursor.fetchall.return_value = [row]

        memories = Memories(database, search_limit=3)
        result = await memories.search(
            user_id="telegram:456",
            query="  PostgreSQL memories  ",
        )

        self.assertEqual(result, [Memory(*row)])
        connection.execute.assert_awaited_once()
        sql, parameters = connection.execute.await_args.args
        self.assertIn("to_tsvector('simple', %s)", sql)
        self.assertIn("array_to_string(lexemes, ' OR ')", sql)
        self.assertIn("websearch_to_tsquery", sql)
        self.assertIn("search_vector @@ parsed_query.value", sql)
        self.assertIn("ts_rank_cd(search_vector, parsed_query.value) DESC", sql)
        self.assertEqual(parameters, ("PostgreSQL memories", "telegram:456", 3))

    async def test_rejects_empty_query(self) -> None:
        database = MagicMock()
        memories = Memories(database, search_limit=10)

        with self.assertRaisesRegex(ValueError, "query must not be empty"):
            await memories.search("telegram:456", "   ")

        database.connection.assert_not_called()

    async def test_rejects_non_positive_search_limit(self) -> None:
        database = MagicMock()

        with self.assertRaisesRegex(ValueError, "greater than zero"):
            Memories(database, search_limit=0)

        database.connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
