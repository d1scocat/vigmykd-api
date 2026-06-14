import httpx
import logging
import uuid

from argon2 import PasswordHasher
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from jwt import JWT
from redis.asyncio import Redis

from vigmykd.routes.v1.account.change_password import models
from vigmykd.services.db import Database
from vigmykd.utils import err, jwt_full_flow_takeover, pwd_is_pwned, pwd_ok


logger = logging.getLogger("account.change_password")


async def change_password(
    query: models.ChangePasswordQuery,
    scheme: str,
    token: str,
    db: Database,
    argon: PasswordHasher,
    redis: Redis,
    jwt: JWT,
):
    log_id = uuid.uuid4()
    logger.info(f"▶️ CHPWDATT {log_id}: {query.invalidate_sessions=}")

    parsed_jwt = await jwt_full_flow_takeover(
        scheme, token, jwt, redis,
        logger, log_id, "CHPWDATT",
    )
    if isinstance(parsed_jwt, JSONResponse):
        return parsed_jwt

    email = parsed_jwt["sub"]
    uid = parsed_jwt["uid"]
    session_id = parsed_jwt["jti"]

    sought = await db.users.find_one({"email": email})
    if not sought:
        await run_in_threadpool(argon.hash, "dummy")
        logger.warning(f"❌ CHPWDATT {log_id} failed: invalid credentials")
        return err(status_code=401, msg="Invalid credentials")

    pw_hash = sought["pwhash"]
    if not await run_in_threadpool(argon.verify, pw_hash, query.old):
        logger.warning(f"❌ CHPWDATT {log_id} failed: invalid credentials")
        return err(status_code=401, msg="Invalid credentials")

    if query.old == query.new:
        return err(status_code=409, msg="The old and new passwords cannot match")

    if not pwd_ok(query.new):
        logger.warning(f"❌ CHPWDATT {log_id} failed: password fails checks")
        return err(400, "Your password does not match the validity criteria")

    try:
        if await pwd_is_pwned(query.new):
            logger.warning(f"❌ CHPWDATT {log_id} failed: password is compromised")
            return err(400, "This password is compromised and should not be used")
    except httpx.RequestError:
        logger.warning(f"❌ CHPWDATT {log_id}: password pwn checker inaccessible"
                       ", will proceed with password change", exc_info=True)

    new_hash = await run_in_threadpool(argon.hash, query.new)
    await db.users.update_one(
        {"email": email},
        {"$set": {"pwhash": new_hash}}
    )

    if query.invalidate_sessions:
        sessions_cur = db.sessions.find({
            "user": uid,
            "session_id": {"$ne": session_id}
        }).batch_size(100)

        async for session in sessions_cur:
            this_id = session["session_id"]
            await db.sessions.delete_one({"session_id": this_id})

            try:
                await redis.delete(f"session:{this_id}")
            except Exception as ex:
                logger.warning(f"⚠️ CHPWDATT {log_id}: "
                               f"Redis invalidation fail: {ex}", exc_info=True)

    logger.info(f"⬆️ CHPWDATT {log_id} succeeded: password changed")
    return Response(status_code=204)
