FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY docker ./docker

RUN chmod +x /app/docker/entrypoint-api.sh /app/docker/entrypoint-worker.sh

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000

CMD ["/app/docker/entrypoint-api.sh"]
