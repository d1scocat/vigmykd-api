from abc import ABC, abstractmethod

from argon2 import PasswordHasher
from fastapi import FastAPI
from jwt import JWT

from vigmykd.settings import config  # loads dotenv also

from vigmykd.packets.communication import UDPClient
from vigmykd.services import db, mailer, redis, ServiceHandler
from vigmykd.tasks import RedisSync


class Starter(ABC):
    @abstractmethod
    async def init(self):
        pass

    @abstractmethod
    async def cleanup(self):
        pass


class DependencyManager(Starter):
    def __init__(self, app: FastAPI):
        self.app = app

    async def init(self):
        self.udp = UDPClient()
        self.redis_service = redis.RedisService(
            url=config.REDIS_URL,
        )

        self.mailer_service = mailer.Mailer(
            smtp_host=config.SMTP_HOST,
            smtp_port=config.SMTP_PORT,
            smtp_user=config.SMTP_USER,
            smtp_pass=config.SMTP_PASS,
        )

        self.db_service = db.Database(
            url=config.DB_URL,
            db_name=config.DB_NAME,
        )

        self.service_handler = ServiceHandler(config.HEALTHCHECK, [
            self.redis_service,
            self.mailer_service,
            self.db_service
        ])

        await self.service_handler.init_services()
        await self.service_handler.start()

        self.app.state.redis = self.redis_service
        self.app.state.mailer = self.mailer_service
        self.app.state.db = self.db_service

        self.app.state.service_handler = self.service_handler

        self.app.state.argon = PasswordHasher(
            time_cost=config.ARGON_TIME_COST,
            memory_cost=config.ARGON_MEMORY_COST,
            parallelism=config.ARGON_PARALLELISM,
            hash_len=config.ARGON_HASH_LENGTH
        )

        self.app.state.jwt = JWT()

    async def cleanup(self):
        self.db_service.shutdown()


class TaskManager(Starter):
    def __init__(self, deps: DependencyManager):
        self.deps = deps

    async def init(self, start: bool = False):
        self.redis_sync = RedisSync(
            redis_service=self.deps.redis_service,
            db_service=self.deps.db_service
        )

        if start:
            await self.start()

    async def start(self):
        await self.redis_sync.start()

    async def cleanup(self):
        await self.redis_sync.stop()
