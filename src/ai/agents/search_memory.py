import re

from langchain_openai import OpenAIEmbeddings
from sqlalchemy import text
from sqlmodel import select

from ai.agent_logging import get_agent_logger, snapshot_context
from ai.agents.memory_operation import RetrievedMemory, SearchMemoryResult
from config import settings
from db_sync import SyncSessionLocal
from models.memory import Memory

log = get_agent_logger("search_memory")

_BM25_UNSAFE = re.compile(r"[^a-zA-Z0-9\s]")


def _sanitize_query(query: str) -> str:
    return _BM25_UNSAFE.sub("", query).strip()


def _rrf_merge(vector_ids: list[int], bm25_ids: list[int], k: int = 60, limit: int = 5) -> list[int]:
    scores: dict[int, float] = {}
    for rank, mid in enumerate(vector_ids, 1):
        scores[mid] = 1 / (k + rank)
    for rank, mid in enumerate(bm25_ids, 1):
        scores[mid] = scores.get(mid, 0) + 1 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)[:limit]


def find_relevant_memories(user_id: int, query: str, limit: int = 5) -> list[Memory]:
    """Hybrid search: vector similarity + BM25 full-text, merged with RRF."""
    log.info(
        "memory_search_started",
        user_id=user_id,
        query=query,
        limit=limit,
        model=settings.embedding_model,
    )

    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        api_key=settings.openai_api_key,
    )
    query_vector = embeddings.embed_query(query)

    with SyncSessionLocal() as session:
        # Vector similarity search (top 10)
        vector_rows = session.execute(
            select(Memory, Memory.embedding.cosine_distance(query_vector).label("distance"))
            .where(Memory.user_id == user_id)
            .where(Memory.embedding.isnot(None))
            .order_by(text("distance"))
            .limit(10)
        ).all()

        vector_ids = [row[0].id for row in vector_rows]
        memory_map = {row[0].id: row[0] for row in vector_rows}

        # BM25 full-text search (top 10)
        sanitized = _sanitize_query(query)
        bm25_ids: list[int] = []
        if sanitized:
            bm25_rows = session.execute(
                text(
                    "SELECT id FROM memory "
                    "WHERE user_id = :user_id "
                    "  AND id @@@ paradedb.parse('content:' || :query) "
                    "ORDER BY paradedb.score(id) DESC "
                    "LIMIT 10"
                ),
                {"user_id": user_id, "query": sanitized},
            ).all()
            bm25_ids = [row[0] for row in bm25_rows]

        # RRF merge
        top_ids = _rrf_merge(vector_ids, bm25_ids, limit=limit)

        # Load any memories only found via BM25
        missing_ids = [mid for mid in top_ids if mid not in memory_map]
        if missing_ids:
            missing = session.execute(
                select(Memory).where(Memory.id.in_(missing_ids))
            ).scalars().all()
            for m in missing:
                memory_map[m.id] = m

        memories = [memory_map[mid] for mid in top_ids if mid in memory_map]

    return memories


def search_memory(user_id: int, query: str) -> SearchMemoryResult:
    memories = find_relevant_memories(user_id, query, limit=5)

    log.info(
        "search_results",
        user_id=user_id,
        count=len(memories),
        agent_context=snapshot_context(
            query=query,
            memories=[{"content": memory.content} for memory in memories],
        ),
    )

    return SearchMemoryResult(
        query=query,
        memories=[
            RetrievedMemory(content=memory.content)
            for memory in memories
        ],
    )
