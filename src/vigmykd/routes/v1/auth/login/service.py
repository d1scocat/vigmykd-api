import logging
import json
import secrets
import string
import uuid

from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi.concurrency import run_in_threadpool
from jwt import JWT
from jwt.utils import get_int_from_datetime
from redis.asyncio import Redis

from vigmykd.services.db import Database
from vigmykd.settings import config, keys
from vigmykd.routes.v1.auth.login import models
from vigmykd.utils import err


alphabet = string.ascii_letters + string.digits


logger = logging.getLogger("auth.login")


async def login(
    query: models.LoginQuery,
    db: Database,
    redis: Redis,
    argon: PasswordHasher,
    jwt: JWT,
):
    log_id = uuid.uuid4()
    logger.info(f"▶️ AUTHATT {log_id}: login={query.login}")

    login = query.login
    key = "email" if "@" in login else "nickname"

    sought = await db.users.find_one({key: login})
    if not sought:
        # constant time
        await run_in_threadpool(argon.hash, "dummy")
        logger.warning(f"❌ AUTHATT {log_id} failed: invalid credentials")
        return err(status_code=401, msg="Invalid credentials")

    pw_hash = sought["pwhash"]
    try:
        # wtf was i thinking
        if not await run_in_threadpool(argon.verify, pw_hash, query.password):
            logger.warning(f"❌ AUTHATT {log_id} failed: invalid credentials")
            return err(status_code=401, msg="Invalid credentials")
    except VerifyMismatchError:
        logger.warning(f"❌ AUTHATT {log_id} failed: invalid credentials")
        return err(status_code=401, msg="Invalid credentials")

    now = datetime.now(timezone.utc)
    exp_in = timedelta(days=config.SESSION_LENGTH_DAYS)
    jwt_ext = get_int_from_datetime(now + exp_in)

    session_id = "".join(secrets.choice(alphabet) for _ in range(config.SESSION_ID_LENGTH))
    sesh_doc = {
        "iat": get_int_from_datetime(now),
        "exp": jwt_ext,
        "user": sought["uuid"],
        "session_id": session_id
    }

    payload = {
        "jti": session_id,
        "sub": sought["email"],
        "name": sought["nickname"],
        "uid": sought["uuid"],
        "iat": get_int_from_datetime(now),
        "exp": jwt_ext,
        "elo": sought["elo"],
        "games_played": sought["games_played"]
    }

    try:
        jws = jwt.encode(payload, keys.private_key, alg="RS256")
    except Exception as ex:
        logger.critical(f"💥 AUTHATT {log_id} failed: could not encode JWT: {ex}", exc_info=True)
        return err(status_code=500, msg="Authentication service is down. Try again later")

    await db.sessions.insert_one(sesh_doc)
    sesh_doc.pop("_id", None)

    try:
        await redis.setex(
            f"session:{session_id}",
            exp_in,
            json.dumps(sesh_doc)
        )
        logger.info(f"💨 AUTHATT {log_id}: saved new session data to Redis")
    except Exception as ex:
        logger.warning(f"⚠️ AUTHATT {log_id}: could not write session to Redis: {ex}",
                       exc_info=True)
        return err(status_code=500, msg="Authentication service is down. Try again later")

    logger.info(f"✅ AUTHATT {log_id} successful, created new session {session_id}")

    return {
        "token": jws,
    }
