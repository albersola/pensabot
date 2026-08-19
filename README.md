# Pensabot

<p align="center">
  <img src="assets/pensabot.png" alt="Pensabot logo" width="200">
</p>

<p align="center">
  <strong>Your second brain, right inside Telegram.</strong><br>
  Send it a note, an idea, or a link. Pensabot remembers it, so you don't have to.
</p>

## Why Pensabot

1. I don't like organizing my notes. 
2. Sometimes you have an idea and you want to put it somewhere, and recover that in the future.
3. I want to have fun with ai agents and memory systems.

## Summary

Pensabot is intentionally simple and you can self host it. The AI agent has two tools:

- **`remember_memory`** — decides what is worth keeping and stores one or more durable memories.
- **`retrieve_memories`** — finds relevant memories with ranked full-text search when you need them again.

> **In progress:** Audio transcription and link summaries are temporarily unavailable while I redesign them.

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
