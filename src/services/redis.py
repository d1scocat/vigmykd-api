from redis.asyncio import Redis

import os


async def init_redis() -> Redis:
    try:
        redis = Redis.from_url(
            os.getenv("REDIS_URL"),
            decode_responses=True,
            socket_timeout=15.0,
            retry_on_timeout=True,
        )

        if await redis.ping():
            print(f"Redis started successfully")
        return redis
    except Exception as ex:
        print(f"Redis startup failed: {ex}")
        raise SystemExit(1)
