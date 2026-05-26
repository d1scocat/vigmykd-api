from argon2 import PasswordHasher
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter.depends import RateLimiter
from jwt import JWT
from pyrate_limiter import Duration, Limiter, Rate
from redis.asyncio import Redis

from vigmykd.dependencies import get_argon, get_db, get_redis, get_jwt
from vigmykd.services.db import Database
from vigmykd.routes.v1.account.change_password import models, service


router = APIRouter()
security = HTTPBearer()


@router.patch(
    "/change-password",
    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 300))))]
)
async def change_password(
    query: models.ChangePasswordQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Database = Depends(get_db),
    argon: PasswordHasher = Depends(get_argon),
    redis: Redis = Depends(get_redis),
    jwt: JWT = Depends(get_jwt),
):
    return await service.change_password(
        query,
        credentials.scheme if credentials else "",
        credentials.credentials if credentials else "",
        db,
        argon,
        redis,
        jwt,
    )
