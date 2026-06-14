from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter
from pyrate_limiter import Duration, Limiter, Rate

from vigmykd.settings import config


router = APIRouter()


@router.get(
    "/public",
#    dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(10, Duration.SECOND * 60))))]
)
async def get_public_key():
    return {"key": Path(config.PUBLIC_KEY_PATH).read_text()}
