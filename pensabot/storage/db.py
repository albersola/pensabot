from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool


class Database:
    """Manage the PostgreSQL connection pool and schema migrations."""

    def __init__(self, url: str) -> None:
        self._pool = AsyncConnectionPool(
            conninfo=url,
            min_size=1,
            max_size=5,
            open=False,
        )

    async def open(self) -> None:
        try:
            await self._pool.open(wait=True)
            await self._apply_migrations()
        except Exception:
            await self._pool.close()
            raise

    async def close(self) -> None:
        await self._pool.close()

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[AsyncConnection]:
        async with self._pool.connection() as connection:
            yield connection

    async def _apply_migrations(self) -> None:
        migration_directory = Path(__file__).resolve().parents[2] / "migrations"
        async with self.connection() as connection:
            await connection.execute("SELECT pg_advisory_xact_lock(706972683)")
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor = await connection.execute("SELECT name FROM schema_migrations")
            applied_migrations = {row[0] for row in await cursor.fetchall()}

            for migration_path in sorted(migration_directory.glob("*.sql")):
                if migration_path.name in applied_migrations:
                    continue

                await self._run_migration(connection, migration_path)
                await connection.execute(
                    "INSERT INTO schema_migrations (name) VALUES (%s)",
                    (migration_path.name,),
                )

    async def _run_migration(
        self,
        connection: AsyncConnection,
        migration_path: Path,
    ) -> None:
        migration = migration_path.read_text(encoding="utf-8")
        statements = [statement.strip() for statement in migration.split(";")]
        for statement in statements:
            if statement:
                await connection.execute(statement)
