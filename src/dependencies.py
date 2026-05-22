from fastapi import HTTPException, Request

from services.redis import RedisService
from services.mailer import Mailer
from services.db import Database
from services import Service, ServiceHandler

from typing import TypeVar


T = TypeVar('T', bound=Service)
async def _get_healthy(request: Request, ambiguous_service: T) -> T:
    service_handler = request.app.state.service_handler
    if not await service_handler.is_healthy(ambiguous_service):
        raise HTTPException(
            status_code=503,
            detail=f"Service {ambiguous_service.__class__.__name__} not healthy"
        )
    
    return ambiguous_service


async def get_redis(request: Request) -> RedisService:
    return await _get_healthy(request, request.app.state.redis)


async def get_mailer(request: Request) -> Mailer:
    return await _get_healthy(request, request.app.state.mailer)


async def get_db(request: Request) -> Database:
    return await _get_healthy(request, request.app.state.db)


def get_service_handler(request: Request) -> ServiceHandler:
    return request.app.state.service_handler
