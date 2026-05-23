from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, Request
from fastapi_limiter.depends import RateLimiter
from pyrate_limiter import Duration, Limiter, Rate
from redis.asyncio import Redis

from dependencies import get_db, get_mailer, get_redis, get_argon
from routes.v1.account.register import models, service
from services.db import Database
from services.mailer import Mailer
from utils import get_real_ip


router = APIRouter()


@router.post(
    "/register",
    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 60))))]
)
async def register(
    query: models.RegisterQuery,
    db: Database = Depends(get_db),
    mailer: Mailer = Depends(get_mailer),
    redis: Redis = Depends(get_redis),
    argon: PasswordHasher = Depends(get_argon),
):
    return await service.register(
        query,
        db,
        mailer,
        redis,
        argon,
    )


@router.post(
    "/register/confirm",
    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 60))))]
)
async def confirm(
    request: Request,
    query: models.ConfirmQuery,
    db: Database = Depends(get_db),
    redis: Redis = Depends(get_redis),
    argon: PasswordHasher = Depends(get_argon),
):
    return await service.confirm(
        query,
        get_real_ip(request),
        db,
        redis,
        argon
    )
