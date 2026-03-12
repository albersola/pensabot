#!/usr/bin/env bash
set -euo pipefail

cd /app

max_attempts=30
attempt=1

until uv run alembic upgrade head; do
  if (( attempt >= max_attempts )); then
    echo "[pensabot] ERROR: failed to run migrations after ${max_attempts} attempts" >&2
    exit 1
  fi
  echo "[pensabot] Database not ready yet, retrying migrations (${attempt}/${max_attempts})..."
  attempt=$((attempt + 1))
  sleep 2
done

exec uv run uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir src
