from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter.depends import RateLimiter
from jwt import JWT
from pyrate_limiter import Duration, Limiter, Rate
from redis.asyncio import Redis

from vigmykd.dependencies import get_db, get_redis, get_jwt
from vigmykd.services.db import Database
from vigmykd.routes.v1.auth.logout import service


router = APIRouter()
security = HTTPBearer()


@router.post(
    "/logout",
#    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 60))))]
)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Database = Depends(get_db),
    redis: Redis = Depends(get_redis),
    jwt: JWT = Depends(get_jwt)
):
    return await service.logout(
        credentials.scheme if credentials else "",
        credentials.credentials if credentials else "",
        db,
        redis,
        jwt,
    )
