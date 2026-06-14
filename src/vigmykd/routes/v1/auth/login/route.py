from argon2 import PasswordHasher
from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter
from jwt import JWT
from pyrate_limiter import Duration, Limiter, Rate
from redis.asyncio import Redis

from vigmykd.dependencies import get_db, get_redis, get_argon, get_jwt
from vigmykd.routes.v1.auth.login import models, service
from vigmykd.services.db import Database


router = APIRouter()


@router.post(
    "/login",
#    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 180))))]
)
async def login(
    query: models.LoginQuery,
    db: Database = Depends(get_db),
    redis: Redis = Depends(get_redis),
    argon: PasswordHasher = Depends(get_argon),
    jwt: JWT = Depends(get_jwt)
):
    return await service.login(
        query,
        db,
        redis,
        argon,
        jwt,
    )
