from redis.asyncio import Redis

import asyncio
import logging

from typing import Awaitable

from vigmykd.settings import config

from vigmykd.services import Service


class RedisService(Service):
    logger = logging.getLogger("services.db")

    def __init__(
        self,
        url: str | None
    ):
        if url is None:
            raise ValueError("RedisService does not accept NoneType arguments. Received: "
                             f"{url=}")

        self.redis = Redis.from_url(
            url,
            decode_responses=True,
            socket_timeout=15.0,
            retry_on_timeout=True,
        )

    async def is_healthy(self) -> bool:
        try:
            return await asyncio.wait_for(
                self._healthcheck(),
                timeout=config.REDIS_HEALTHCHECK_TIMEOUT
            )
        except asyncio.TimeoutError:
            self.logger.error("❌ REDIS HEALTH CHECK FAIL: Timed out")
        except Exception:
            # self.logger.error(f"❌ SMTP REDIS CHECK FAIL: Unknown exception: {ex}")
            # delegate to service_handler
            raise
        return False

    async def _healthcheck(self):
        pong = self.redis.ping()  # bool | Awaitable[bool]

        if isinstance(pong, Awaitable):
            return await pong
        elif isinstance(pong, bool):
            return pong
        else:
            return False

    async def init(self):
        if not await self.is_healthy():
            self.logger.error("❌ SMTP REDIS INIT FAIL")
            raise SystemExit(1)
