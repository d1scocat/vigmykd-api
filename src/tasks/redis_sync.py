import asyncio
import json
import logging

from datetime import datetime, timezone

from settings import config
from services.db import Database
from services.redis import RedisService


class RedisSync:
    logger = logging.getLogger("tasks.redis_sync")

    def __init__(
        self,
        db_service: Database,
        redis_service: RedisService
    ):
        self.db_service = db_service
        self.redis_service = redis_service

        self._shutdown_event = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def start(self):
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._sync_loop())
        self.logger.info("▶️ Started Redis-Mongo session sync task")

    async def stop(self):
        if self._task and not self._task.done():
            self._shutdown_event.set()
            await self._task
            self.logger.info("🛑 Redis-Mongo session sync task stopped")

    async def _sync_loop(self):
        while not self._shutdown_event.is_set():
            try:
                await self.sync_once()
            except Exception as ex:
                self.logger.warning(f"⚠️ Redis-Mongo sync task failed once: {ex}", exc_info=True)

            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=config.REDIS_SESSION_SYNC_PERIOD
                )
                break
            except asyncio.TimeoutError:
                continue

    async def sync_once(self):
        if not await self.db_service.is_healthy():
            self.logger.warning("⚠️ Could not sync sessions - MongoDB is unhealthy")
            return

        if not await self.redis_service.is_healthy():
            self.logger.warning("⚠️ Could not sync sessions - Redis is unhealthy")
            return

        sessions = [doc async for doc in self.db_service.sessions.find()]
        user_uuids = list(set([doc["user"] for doc in sessions]))
        users_cursor = self.db_service.users.find({"uuid": {"$in": user_uuids}})
        users_by_uuid = {str(user["uuid"]): user async for user in users_cursor}

        pipe = self.redis_service.redis.pipeline(transaction=False)
        now = int(datetime.now(timezone.utc).timestamp())

        for sesh_doc in sessions:
            sesh_doc.pop("_id", None)

            uuid = sesh_doc["user"]
            user = users_by_uuid.get(uuid)
            if not user:
                self.logger.warning(f"⚠️ Did not find a user for {uuid=} while syncing sessions")
                continue

            session_id = sesh_doc["session_id"]
            exp = sesh_doc["exp"]
            ttl = exp - now

            if ttl <= 0:
                pipe.delete(f"session:{session_id}")
                # await self.db_service.sessions.delete_one({"session_id": session_id})
                # ^^^ extract the above to its own task later on, it should be decoupled
                # from a sync task because mongodb is authoritative after all
                continue

            pipe.setex(
                f"session:{session_id}",
                ttl,
                json.dumps(sesh_doc)
            )

        results = await pipe.execute()
        self.logger.info(f"▶️ Redis-Mongo sync task completed successfully | {results=}")
