from pensabot.models.memory import Memory
from pensabot.storage.db import Database


class Memories:
    """Persist durable facts about users in PostgreSQL."""

    def __init__(self, database: Database, search_limit: int) -> None:
        if search_limit <= 0:
            raise ValueError("search_limit must be greater than zero")

        self._database = database
        self._search_limit = search_limit

    async def upsert(
        self,
        user_id: str,
        memory_key: str,
        content: str,
        source_conversation_id: str,
    ) -> Memory:
        query = """
            INSERT INTO memories (
                user_id,
                memory_key,
                content,
                source_conversation_id
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, memory_key) DO UPDATE
            SET content = EXCLUDED.content,
                source_conversation_id = EXCLUDED.source_conversation_id,
                updated_at = CASE
                    WHEN memories.content IS DISTINCT FROM EXCLUDED.content
                    THEN NOW()
                    ELSE memories.updated_at
                END
            RETURNING
                id,
                user_id,
                memory_key,
                content,
                source_conversation_id,
                created_at,
                updated_at
        """
        async with self._database.connection() as connection:
            cursor = await connection.execute(
                query,
                (user_id, memory_key, content, source_conversation_id),
            )
            row = await cursor.fetchone()

        if row is None:
            raise RuntimeError("Memory upsert did not return a row")

        return Memory(*row)

    async def search(
        self,
        user_id: str,
        query: str,
    ) -> list[Memory]:
        """Return the current user's memories matching a full-text query."""
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty")

        search_query = """
            WITH query_lexemes AS (
                -- Parse user input as plain text before adding search operators.
                SELECT tsvector_to_array(
                    to_tsvector('simple', %s)
                ) AS lexemes
            ),
            parsed_query AS (
                SELECT websearch_to_tsquery(
                    'simple',
                    array_to_string(lexemes, ' OR ')
                ) AS value
                FROM query_lexemes
            )
            SELECT
                id,
                user_id,
                memory_key,
                content,
                source_conversation_id,
                created_at,
                updated_at
            FROM memories
            CROSS JOIN parsed_query
            WHERE user_id = %s
              AND search_vector @@ parsed_query.value
            ORDER BY
                ts_rank_cd(search_vector, parsed_query.value) DESC,
                updated_at DESC,
                id DESC
            LIMIT %s
        """
        async with self._database.connection() as connection:
            cursor = await connection.execute(
                search_query,
                (normalized_query, user_id, self._search_limit),
            )
            rows = await cursor.fetchall()

        return [Memory(*row) for row in rows]
