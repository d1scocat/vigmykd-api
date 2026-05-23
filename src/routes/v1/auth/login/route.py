from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter.depends import RateLimiter
from pyrate_limiter import Duration, Limiter, Rate

from routes.v1.auth.login import models


router = APIRouter()
security = HTTPBearer()


@router.post(
    "/login",
    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 60))))]
)
async def login(
    query: models.LoginQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # credentials.scheme -> "Bearer"
    # credentials.credentials -> "<token>"
    pass
