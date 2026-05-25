import logging
import uuid

from fastapi import Response
from fastapi.responses import JSONResponse
from jwt import JWT
from redis.asyncio import Redis

from services.db import Database
from utils import jwt_full_flow_takeover


logger = logging.getLogger("auth.logout")


async def logout(
    scheme: str,
    token: str,
    db: Database,
    redis: Redis,
    jwt: JWT,
):
    log_id = uuid.uuid4()
    logger.info(f"▶️ LOGOUTATT {log_id}")

    parsed_jwt = await jwt_full_flow_takeover(
        scheme, token, jwt, redis,
        logger, log_id, "LOGOUTATT",
    )
    if isinstance(parsed_jwt, JSONResponse):
        return parsed_jwt

    session_id = parsed_jwt["jti"]  # guaranteed to exist at this point

    await db.sessions.delete_one({"session_id": session_id})
    
    try:
        await redis.delete(f"session:{session_id}")
    except Exception as ex:
        logger.warning(f"⚠️ LOGOUTATT {log_id}: Redis invalidation fail: {ex}", exc_info=True)

    return Response(status_code=204)