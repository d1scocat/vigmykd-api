import json
import logging
import uuid

from datetime import datetime, timezone, timedelta

from fastapi.responses import JSONResponse, RedirectResponse
from jwt import JWT
from redis.asyncio import Redis

from settings import config

from routes.v1.account.delete import models
from services.db import Database
from services.mailer import Mailer, PreaggregatedMailer
from utils import err, jwt_full_flow_takeover


d_logger = logging.getLogger("account.delete")
c_logger = logging.getLogger("account.delete.confirm")


async def delete(
    scheme: str,
    token: str,
    db: Database,
    mailer: Mailer,
    redis: Redis,
    jwt: JWT,
):
    log_id = uuid.uuid4()
    d_logger.info(f"▶️ DELATT {log_id}")

    parsed_jwt = await jwt_full_flow_takeover(
        scheme, token, jwt, redis,
        d_logger, log_id, "DELATT",
    )
    if isinstance(parsed_jwt, JSONResponse):
        return parsed_jwt

    del_confirm_code = str(uuid.uuid4())
    await redis.setex(
        f"delconfirm:{del_confirm_code}",
        config.REG_CONFIRM_CODE_TTL,
        json.dumps({
            "type": "del",
            "uid": parsed_jwt["uid"]
        })
    )

    email = parsed_jwt["sub"]
    if not await PreaggregatedMailer.send_del_confirmation(
        mailer=mailer,
        receiver=email,
        code=del_confirm_code
    ):
        d_logger.error(f"❌ DELATT {log_id}: Failed to send confirmation email to {email}")
        await redis.delete(f"delconfirm:{del_confirm_code}")
        return err(500, "Could not send the registration confirmation email, try again")

    d_logger.info(f"▶️ DELATT {log_id} continues to confirm stage: successfully sent code email")

    redirect = f"{config.BASE_URL}/api/v1/account/delete/confirm"
    return RedirectResponse(
        url=redirect,
        status_code=303,
    )


async def confirm(
    query: models.ConfirmQuery,
    scheme: str,
    token: str,
    ip: str,
    db: Database,
    redis: Redis,
    jwt: JWT,
):
    log_id = uuid.uuid4()
    c_logger.info(f"▶️ DELCONFATT {log_id}")

    # ratelimit impl
    lockout_key = f"lockout:ip:{ip}:account_delete_confirm"
    fail_key = f"failcount:ip:{ip}:account_delete_confirm"

    if await redis.exists(lockout_key):
        c_logger.warning(f"🔐 DELCONFATT {log_id}: rate-limited for {ip}")
        return err(429, "Too many requests, try again later")

    async def fail(status: int, msg: str):
        fail_count = await redis.incr(fail_key)

        if fail_count == 1:
            c_logger.info(f"📊 DELCONFATT {log_id}: Failure count for {ip} = "
                        f"{fail_count}/{config.FAIL_COUNT_TO_CONFIRM_RATELIMIT}")
            await redis.expire(fail_key, config.CONFIRM_RATELIMIT_SECONDS)

        if fail_count >= config.FAIL_COUNT_TO_CONFIRM_RATELIMIT:
            await redis.setex(lockout_key, config.CONFIRM_RATELIMIT_SECONDS, "1")
            c_logger.warning(f"🔒 DELCONFATT {log_id}: rate-locked {ip} "
                         f"after {config.FAIL_COUNT_TO_CONFIRM_RATELIMIT} fails")
            return err(429, "Too many requests, try again later")

        return err(status, msg)

    parsed_jwt = await jwt_full_flow_takeover(
        scheme, token, jwt, redis,
        c_logger, log_id, "DELCONFATT",
    )
    if isinstance(parsed_jwt, JSONResponse):
        return parsed_jwt

    value = await redis.getdel(f"delconfirm:{query.code}")
    if value is None:
        c_logger.info(f"⚠️ DELCONFATT {log_id}: {query.code=} not found (expired/invalid/used)")
        return await fail(401, "The code is not valid.")

    try:
        res = json.loads(value)
    except json.JSONDecodeError:
        c_logger.warning(f"❌ DELCONFATT {log_id} failed: Corrupted payload for {query.code=}: {value}")
        return await fail(500, "The code has been corrupted. "
                               "Please restart the registration process")

    if parsed_jwt["uid"] != res["uid"]:
        return err(401, "Token does not match deletion request")

    if not {"type", "uid"}.issubset(res.keys()):
        c_logger.warning(f"❌ DELCONFATT {log_id} failed: {query.code=} was malformed: {res}")
        return await fail(500, "The code has been corrupted. "
                               "Please restart the registration process")

    uid = res["uid"]

    try:
        result = await db.users.find_one_and_delete({"uuid": uid})
        if not result:
            c_logger.warning(f"⚠️ DELCONFATT {log_id}: User {uid} not found (already deleted?)")
        else:
            now = datetime.now(timezone.utc)
            exp = now + timedelta(days=config.DELETED_ACCOUNTS_TTL_DAYS)
            result.update({"deleted_at": now, "exp": exp})

            await db.deleted.insert_one(result)
    except Exception as ex:
        c_logger.error(f"❌ DELCONFATT {log_id}: MongoDB deletion failed: {ex}", exc_info=True)
        return err(500, "Deletion failed temporarily, please try again")

    c_logger.info(f"▶️ DELCONFATT {log_id} successful: deleted account by {uid}")

    redirect = f"{config.BASE_URL}/api/v1/account/register"
    return RedirectResponse(
        url=redirect,
        status_code=303,
    )
