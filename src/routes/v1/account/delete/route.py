from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter.depends import RateLimiter
from pyrate_limiter import Duration, Limiter, Rate

from routes.v1.account.delete import models


router = APIRouter()
security = HTTPBearer()


@router.delete(
    "/delete",
    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 60))))]
)
async def delete(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # credentials.scheme -> "Bearer"
    # credentials.credentials -> "<token>"
    pass


@router.post(
    "/delete/confirm",
    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 60))))]
)
async def confirm(
    query: models.ConfirmQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    pass
