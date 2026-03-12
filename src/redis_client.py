from redis import Redis as SyncRedis
from redis.asyncio import Redis

from config import settings

redis_client: Redis | None = None
sync_redis_client: SyncRedis | None = None


async def init_redis() -> Redis:
    global redis_client
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return redis_client


async def close_redis() -> None:
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None


def get_redis() -> Redis:
    assert redis_client is not None, "Redis not initialized"
    return redis_client


def get_sync_redis() -> SyncRedis:
    global sync_redis_client
    if sync_redis_client is None:
        sync_redis_client = SyncRedis.from_url(settings.redis_url, decode_responses=True)
    return sync_redis_client
