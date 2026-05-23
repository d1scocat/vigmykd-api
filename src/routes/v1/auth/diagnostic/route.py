from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter.depends import RateLimiter
from pyrate_limiter import Duration, Limiter, Rate


router = APIRouter(prefix="/diagnostic")
security = HTTPBearer()


@router.get(
    "/validate-token",
    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 60))))]
)
async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # credentials.scheme -> "Bearer"
    # credentials.credentials -> "<token>"
    pass
