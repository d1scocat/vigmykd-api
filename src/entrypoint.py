import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

import config  # loads dotenv also

from services import db, redis, mailer
from routes.router import v1_router


@asynccontextmanager
async def lifespan(api: FastAPI):
    api.state.redis = await redis.init_redis()

    api.state.mailer = mailer.Mailer(
        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=os.getenv("SMTP_PORT"),
        smtp_user=os.getenv("SMTP_USER"),
        smtp_pass=os.getenv("SMTP_PASS")
    )

    database = db.Database(
        url=os.getenv("DB_URL"),
        db_name=os.getenv("DB_NAME")
    )
    await database.init()

    api.state.db = database

    yield

    database._client.close()


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
