import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

import config  # loads dotenv also

from services import db, redis, mailer, ServiceHandler
from routes.router import v1_router


@asynccontextmanager
async def lifespan(api: FastAPI):
    redis_service = redis.RedisService(
        url=os.getenv("REDIS_URL")
    )

    mailer_service = mailer.Mailer(
        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=os.getenv("SMTP_PORT"),
        smtp_user=os.getenv("SMTP_USER"),
        smtp_pass=os.getenv("SMTP_PASS")
    )

    db_service = db.Database(
        url=os.getenv("DB_URL"),
        db_name=os.getenv("DB_NAME")
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

    yield

    db_service._client.close()


def make_app() -> FastAPI:
    app = FastAPI(
        title="vigmykd REST API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)

    return app


app = make_app()

# Launch with:
# uvicorn entrypoint:app --workers <amount of workers>
