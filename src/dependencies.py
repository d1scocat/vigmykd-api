from fastapi import HTTPException, Request
from redis.asyncio import Redis

from services.mailer import Mailer
from services.db import Database


def get_redis(request: Request) -> Redis:
    client = request.app.state.redis
    if client is None:
        raise HTTPException(status_code=503, detail="Redis not initialized")

    return client


def get_mailer(request: Request) -> Mailer:
    return request.app.state.mailer


def get_db(request: Request) -> Database:
    return request.app.state.db
