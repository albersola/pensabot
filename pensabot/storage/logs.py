from collections.abc import Mapping

from psycopg.types.json import Jsonb

from pensabot.models.log import Log
from pensabot.storage.db import Database


class Logs:
    """Store append-only application events in PostgreSQL."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def append(
        self,
        event: str,
        *,
        user_id: str | None = None,
        conversation_id: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> Log:
        query = """
            INSERT INTO logs (
                user_id,
                conversation_id,
                event,
                details
            )
            VALUES (%s, %s, %s, %s)
            RETURNING
                id,
                user_id,
                conversation_id,
                event,
                details,
                created_at
        """
        async with self._database.connection() as connection:
            cursor = await connection.execute(
                query,
                (
                    user_id,
                    conversation_id,
                    event,
                    Jsonb(dict(details or {})),
                ),
            )
            row = await cursor.fetchone()

        if row is None:
            raise RuntimeError("Log insert did not return a row")

        return Log(*row)
