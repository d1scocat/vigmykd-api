import logging
import os
import time

from argon2 import PasswordHasher
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from settings import config  # loads dotenv also

from log import setup as setup_log
from routes.router import v1_router
from services import db, redis, mailer, ServiceHandler
from utils import err


logger = logging.getLogger("core")


@asynccontextmanager
async def lifespan(api: FastAPI):
    start = time.monotonic()

    setup_log.setup()

    redis_service = redis.RedisService(
        url=config.REDIS_URL,
    )

    mailer_service = mailer.Mailer(
        smtp_host=config.SMTP_HOST,
        smtp_port=config.SMTP_PORT,
        smtp_user=config.SMTP_USER,
        smtp_pass=config.SMTP_PASS,
    )

    db_service = db.Database(
        url=config.DB_URL,
        db_name=config.DB_NAME,
    )

    service_handler = ServiceHandler(config.HEALTHCHECK, [
        redis_service,
        mailer_service,
        db_service
    ])

    await service_handler.init_services()
    await service_handler.start()

    api.state.redis = redis_service
    api.state.mailer = mailer_service
    api.state.db = db_service

    api.state.service_handler = service_handler

    api.state.argon = PasswordHasher(
        time_cost=config.ARGON_TIME_COST,
        memory_cost=config.ARGON_MEMORY_COST,
        parallelism=config.ARGON_PARALLELISM,
        hash_len=config.ARGON_HASH_LENGTH
    )

    elapsed = time.monotonic() - start
    logger.info(f"⏱️ vigmykd REST API successfully started in {elapsed}s\n")

    yield

    db_service.shutdown()


def make_app() -> FastAPI:
    app = FastAPI(
        title="vigmykd REST API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://vigmykd.runderscore.com"
        ],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.include_router(v1_router)

    return app


app = make_app()


@app.middleware("http")
async def handle_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except HTTPException as ex:
        return err(status_code=ex.status_code, msg=ex.detail)
    except Exception as ex:
        logger.error(f"❌ Uncaught exception: {ex}", exc_info=True)
        return err(status_code=500, msg=f"{ex}")

# Launch with:
# uvicorn entrypoint:app --workers <amount of workers>
