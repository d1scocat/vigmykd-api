from fastapi import APIRouter, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from dependencies import get_db, get_mailer, get_redis
from routes.v1.account.register import models, service
from services.db import Database
from services.mailer import Mailer
from services.redis import RedisService


router = APIRouter()
security = HTTPBearer()


@router.post("/register")
async def register(
    response: Response,
    query: models.RegisterQuery,
    db: Database = Depends(get_db),
    mailer: Mailer = Depends(get_mailer),
    redis: RedisService = Depends(get_redis),
):
    return await service.register(
        query,
        db,
        mailer,
        redis,
    )
    

    # credentials.scheme -> "Bearer"
    # credentials.credentials -> "<token>"
    pass


@router.post("/register/confirm")
async def confirm(
    query: models.ConfirmQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    pass
