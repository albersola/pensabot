import secrets

from redis.asyncio import Redis

LINK_TTL = 1800  # 30 minutes


async def create_link_code(user_id: int, redis: Redis) -> str:
    code = secrets.token_urlsafe(6)
    await redis.set(f"link:{code}", str(user_id), ex=LINK_TTL)
    return code


async def resolve_link_code(code: str, redis: Redis) -> int | None:
    val = await redis.get(f"link:{code}")
    if val is None:
        return None
    await redis.delete(f"link:{code}")
    return int(val)
