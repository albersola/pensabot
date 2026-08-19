# Pensabot

![Pensabot logo](assets/pensabot.png)

Pensabot is a second brain AI Agent that lives in a Telegram chat.

Send anything you want to keep in a chat (a note, an idea, a link), and forget about it. Pensabot will remember it on its memory for you.

I want to keep the bot simple right now. It has two tools:
- remember_memory: the agent can decide based on the user message to store one or more memories.
- retrieve_memories: the agent can generate a query to search user memories. Right now the implementation looks for memories using word matching and ranks them.

> Audio transcription and link summaries are temporarily unavailable while I redesign them.

## Why Pensabot

1. I don't like organizing my notes. 
2. Sometimes you have an idea and you want to put it somewhere, and recover that in the future.
3. I want to have fun with ai agents and memory systems.

[Read more about it in my blog.](https://www.pirobits.com/es/blog/pensabot-remember-anything-from-telegram)

## Quick start

1. Install dependencies and start PostgreSQL:

   ```sh
   uv sync
   docker compose up -d postgres
   ```

2. Create `.env`:

   ```dotenv
   OPENAI_API_KEY=your_openai_api_key
   DATABASE_URL=postgresql://pensabot:pensabot@localhost:5432/pensabot
   MEMORY_MAX_MESSAGES=20
   MEMORY_SEARCH_LIMIT=10

   TELEGRAM_API_KEY=your_bot_token
   ALLOWED_CHATS=123456789,987654321
   ```

3. Apply migrations:

   ```sh
   uv run python main.py --migrate
   ```

4. Run an interface:

   ```sh
   uv run python main.py --interface telegram
   uv run python main.py --interface cli
   ```

The CLI keeps its history under `cli:local`. Telegram keeps separate history for
each chat ID. Use `/quit` or `/exit` to leave the CLI.

## Database

Pending migrations from [`migrations/`](migrations/) are applied by
`--migrate` and automatically whenever Pensabot starts.

The database contains three application tables with matching Python models and
repositories:

- `chats` stores conversation messages with both user and conversation IDs.
- `memories` stores durable user facts keyed by `(user_id, memory_key)`.
- `logs` stores append-only application events, including memory writes.

Useful local PostgreSQL commands:

```sh
docker compose ps
docker compose logs -f postgres
docker compose down
```

The named Docker volume preserves data across container restarts. Run
`docker compose down --volumes` only when you intentionally want to delete the
local database.

## Tests

```sh
uv run python -m unittest
```
