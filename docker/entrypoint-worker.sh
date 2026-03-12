#!/usr/bin/env bash
set -euo pipefail

cd /app/src

exec uv run celery -A celery_app worker --loglevel=info --pool=gevent --concurrency="${CELERY_CONCURRENCY:-1}"
