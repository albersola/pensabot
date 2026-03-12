from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import islice
from typing import Any

import structlog

MAX_CONTEXT_STRING_LENGTH = 1500
MAX_CONTEXT_COLLECTION_ITEMS = 10
MAX_CONTEXT_DEPTH = 4


def get_agent_logger(agent_name: str):
    return structlog.get_logger().bind(agent_name=agent_name)


def log_agent_invocation(log, *, model: str | None = None, **context: Any) -> None:
    event: dict[str, Any] = {"agent_context": snapshot_context(**context)}
    if model:
        event["model"] = model
    log.info("agent_invoked", **event)


def snapshot_context(**context: Any) -> dict[str, Any]:
    return {key: _serialize_value(value, depth=0) for key, value in context.items()}


def _serialize_value(value: Any, *, depth: int) -> Any:
    if depth >= MAX_CONTEXT_DEPTH:
        return "<max-depth>"

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        return _truncate_text(value)

    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"

    if isinstance(value, Mapping):
        items = list(islice(value.items(), MAX_CONTEXT_COLLECTION_ITEMS + 1))
        serialized = {
            str(key): _serialize_value(item, depth=depth + 1)
            for key, item in items[:MAX_CONTEXT_COLLECTION_ITEMS]
        }
        if len(items) > MAX_CONTEXT_COLLECTION_ITEMS:
            serialized["__truncated__"] = True
        return serialized

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = list(islice(value, MAX_CONTEXT_COLLECTION_ITEMS + 1))
        serialized = [_serialize_value(item, depth=depth + 1) for item in items[:MAX_CONTEXT_COLLECTION_ITEMS]]
        if len(items) > MAX_CONTEXT_COLLECTION_ITEMS:
            serialized.append("<truncated>")
        return serialized

    return _truncate_text(repr(value))


def _truncate_text(value: str) -> str:
    normalized = value.strip()
    if len(normalized) <= MAX_CONTEXT_STRING_LENGTH:
        return normalized
    remainder = len(normalized) - MAX_CONTEXT_STRING_LENGTH
    return f"{normalized[:MAX_CONTEXT_STRING_LENGTH]}...<truncated {remainder} chars>"
