from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter.depends import RateLimiter
from jwt import JWT
from pyrate_limiter import Duration, Limiter, Rate
from redis.asyncio import Redis

from vigmykd.dependencies import get_redis, get_jwt, get_udp
from vigmykd.packets.communication import UDPClient
from vigmykd.routes.v1.matchmaking.start import service


router = APIRouter()
security = HTTPBearer()


@router.post(
    "/start",
    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(20, Duration.SECOND * 60))))]
)
async def start(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis: Redis = Depends(get_redis),
    jwt: JWT = Depends(get_jwt),
    udp: UDPClient = Depends(get_udp)
):
    return await service.start(
        credentials.scheme if credentials else "",
        credentials.credentials if credentials else "",
        redis,
        jwt,
        udp,
    )
