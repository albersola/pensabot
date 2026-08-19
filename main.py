import argparse
import asyncio
from collections.abc import Sequence

from dotenv import load_dotenv

from pensabot.config import (
    ConfigurationError,
    load_database_config,
    load_telegram_config,
)
from pensabot.core import handle_message
from pensabot.interfaces.cli import run_cli
from pensabot.interfaces.telegram import run_telegram
from pensabot.storage import Chats, Database, Logs, Memories


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Pensabot")
    parser.add_argument(
        "--interface",
        choices=("telegram", "cli"),
        default="telegram",
        help="interface to run (default: telegram)",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="apply pending database migrations and exit",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> None:
    parser = create_argument_parser()
    options = parser.parse_args(arguments)

    load_dotenv()

    try:
        database_config = load_database_config()
    except ConfigurationError as error:
        parser.error(str(error))

    database = Database(database_config.url)

    if options.migrate:
        asyncio.run(run_migrations(database))
        return

    chats = Chats(
        database=database,
        recent_message_limit=database_config.recent_message_limit,
    )
    memories = Memories(
        database=database,
        search_limit=database_config.memory_search_limit,
    )
    logs = Logs(database)

    if options.interface == "cli":
        asyncio.run(run_cli_application(database, chats, memories, logs))
        return

    try:
        config = load_telegram_config()
    except ConfigurationError as error:
        parser.error(str(error))

    run_telegram(config, database, chats, memories, logs)


async def run_migrations(database: Database) -> None:
    await database.open()
    await database.close()
    print("Database migrations applied.")


async def run_cli_application(
    database: Database,
    chats: Chats,
    memories: Memories,
    logs: Logs,
) -> None:
    async def process_message(
        text: str,
        user_id: str,
        conversation_id: str,
    ) -> str:
        return await handle_message(
            text,
            user_id,
            conversation_id,
            chats,
            memories,
            logs,
        )

    await database.open()
    try:
        await run_cli(process_message)
    finally:
        await database.close()


if __name__ == "__main__":
    main()
