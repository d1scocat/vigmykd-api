from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter.depends import RateLimiter
from jwt import JWT
from pyrate_limiter import Duration, Limiter, Rate
from redis.asyncio import Redis

from vigmykd.dependencies import get_db
from vigmykd.routes.v1.matchmaking.end import models, service
from vigmykd.services.db import Database


router = APIRouter()
security = HTTPBearer()


@router.post(
    "/end"
)
async def end(
    query: models.GameOverQuery,
    database: Database = Depends(get_db),
):
    return await service.end(
        query,
        database
    )
