from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter.depends import RateLimiter
from jwt import JWT
from pyrate_limiter import Duration, Limiter, Rate
from redis.asyncio import Redis

from vigmykd.dependencies import get_redis, get_jwt
from vigmykd.routes.v1.auth.diagnostic import service


router = APIRouter(prefix="/diagnostic")
security = HTTPBearer(auto_error=False)


@router.get(
    "/validate-token",
    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 60))))]
)
async def validate_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    redis: Redis = Depends(get_redis),
    jwt: JWT = Depends(get_jwt)
):
    return await service.validate(
        credentials.scheme if credentials else "",
        credentials.credentials if credentials else "",
        redis,
        jwt
    )
