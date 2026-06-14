from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter.depends import RateLimiter
from jwt import JWT
from pyrate_limiter import Duration, Limiter, Rate
from redis.asyncio import Redis

from vigmykd.dependencies import get_db, get_jwt, get_mailer, get_redis
from vigmykd.routes.v1.account.delete import models, service
from vigmykd.services.db import Database
from vigmykd.services.mailer import Mailer
from vigmykd.utils import get_real_ip


router = APIRouter()
security = HTTPBearer()


@router.delete(
    "/delete",
#    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(3, Duration.SECOND * 60))))]
)
async def delete(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Database = Depends(get_db),
    mailer: Mailer = Depends(get_mailer),
    redis: Redis = Depends(get_redis),
    jwt: JWT = Depends(get_jwt),
):
    return await service.delete(
        credentials.scheme if credentials else "",
        credentials.credentials if credentials else "",
        db,
        mailer,
        redis,
        jwt,
    )


@router.post(
    "/delete/confirm",
#    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(3, Duration.SECOND * 60))))]
)
async def confirm(
    request: Request,
    query: models.ConfirmQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Database = Depends(get_db),
    redis: Redis = Depends(get_redis),
    jwt: JWT = Depends(get_jwt),
):
    return await service.confirm(
        query,
        credentials.scheme if credentials else "",
        credentials.credentials if credentials else "",
        get_real_ip(request),
        db,
        redis,
        jwt,
    )
