import json
import httpx
import logging
import uuid
import time

from argon2 import PasswordHasher
from email_validator import validate_email, EmailNotValidError
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse
from pymongo.errors import DuplicateKeyError
from redis.asyncio import Redis

from vigmykd.settings import config

from vigmykd.routes.v1.account.register import models
from vigmykd.services.db import Database
from vigmykd.services.mailer import Mailer, PreaggregatedMailer
from vigmykd.utils import err, pwd_ok, pwd_is_pwned, name_ok


r_logger = logging.getLogger("account.register")
c_logger = logging.getLogger("account.register.confirm")


async def register(
    query: models.RegisterQuery,
    db: Database,
    mailer: Mailer,
    redis: Redis,
    argon: PasswordHasher,
):
    log_id = uuid.uuid4()
    r_logger.info(f"▶️ REGATT {log_id}: email={query.email}, nickname={query.nickname}")

    if not query.agree_with_policies:
        r_logger.warning(f"❌ REGATT {log_id} failed: query.agree_with_policies=False")
        return err(400, "You must agree to the policies in order to register")

    if not name_ok(query.nickname):
        r_logger.warning(f"❌ REGATT {log_id} failed: {query.nickname=} fails checks")
        return err(400, f"The nickname {query.nickname} does not match the validity criteria")

    conflict = await db.users.find_one({
        "$or": [
            {"nickname": query.nickname},
            {"email": query.email},
        ]
    })

    if conflict:
        if conflict["nickname"] == query.nickname:
            r_logger.warning(f"❌ REGATT {log_id} failed: {query.nickname=} is in use")
            return err(409, f"Nickname {query.nickname} is already in use")
        else:
            r_logger.warning(f"❌ REGATT {log_id} failed: {query.email=} is in use")
            return err(409, f"Email {query.email} is already in use")

    try:
        _ = validate_email(query.email, check_deliverability=False)
    except EmailNotValidError:
        r_logger.warning(f"❌ REGATT {log_id} failed: {query.email=} is invalid")
        return err(400, f"The email {query.email} is invalid or unreachable")

    if not pwd_ok(query.password):
        r_logger.warning(f"❌ REGATT {log_id} failed: password fails checks")
        return err(400, "Your password does not match the validity criteria")

    try:
        if await pwd_is_pwned(query.password):
            r_logger.warning(f"❌ REGATT {log_id} failed: password is compromised")
            return err(400, "This password is compromised and should not be used")
    except httpx.RequestError:
        r_logger.warning(f"❌ REGATT {log_id}: password pwn checker inaccessible, "
                         "will proceed with registration", exc_info=True)
        # return err(500, "Could not check for password presence in data breaches")

    reg_confirm_code = str(uuid.uuid4())
    pwhash = await run_in_threadpool(argon.hash, query.password)
    await redis.setex(
        f"regconfirm:{reg_confirm_code}",
        config.REG_CONFIRM_CODE_TTL,
        json.dumps({
            "type": "reg",
            "email": query.email,
            "pwhash": pwhash,
            "nickname": query.nickname
        })
    )

    if not await PreaggregatedMailer.send_reg_confirmation(
        mailer=mailer,
        receiver=query.email,
        code=reg_confirm_code
    ):
        r_logger.error(f"❌ REGATT {log_id}: Failed to send confirmation email to {query.email}")
        await redis.delete(f"regconfirm:{reg_confirm_code}")
        return err(500, "Could not send the registration confirmation email, try again")

    r_logger.info(f"▶️ REGATT {log_id} continues to confirm stage: successfully sent code email")

    redirect = f"{config.BASE_URL}/api/v1/account/register/confirm"
    return RedirectResponse(
        url=redirect,
        status_code=303,
    )


async def confirm(
    query: models.ConfirmQuery,
    ip: str,
    db: Database,
    redis: Redis,
    argon: PasswordHasher,
):
    # recheck nickname and email validity, because while the code was
    # pending to be accepted, they could have been taken already
    log_id = uuid.uuid4()
    r_logger.info(f"▶️ REGCONFATT {log_id}")

    start = time.monotonic()

    async def ensure_constant_time():
        elapsed = time.monotonic() - start
        if elapsed < config.MIN_CONFIRM_EXEC_TIME:
            while time.monotonic() - start < config.MIN_CONFIRM_EXEC_TIME:
                await run_in_threadpool(argon.hash, "dummy")

    if not ip:
        c_logger.warning(f"❌ REGCONFATT {log_id} failed: no IP available")
        return err(400, "Could not fetch your IP address")

    # ratelimit impl
    lockout_key = f"lockout:ip:{ip}:account_register_confirm"
    fail_key = f"failcount:ip:{ip}:account_register_confirm"

    if await redis.exists(lockout_key):
        await run_in_threadpool(argon.hash, "dummy")
        c_logger.warning(f"🔐 REGCONFATT {log_id}: rate-limited for {ip}")
        return err(429, "Too many requests, try again later")

    async def fail(status: int, msg: str):
        await ensure_constant_time()

        fail_count = await redis.incr(fail_key)

        if fail_count == 1:
            c_logger.info(f"📊 REGCONFATT {log_id}: Failure count for {ip} = "
                          f"{fail_count}/{config.FAIL_COUNT_TO_CONFIRM_RATELIMIT}")
            await redis.expire(fail_key, config.CONFIRM_RATELIMIT_SECONDS)

        if fail_count >= config.FAIL_COUNT_TO_CONFIRM_RATELIMIT:
            await redis.setex(lockout_key, config.CONFIRM_RATELIMIT_SECONDS, "1")
            c_logger.warning(f"🔒 REGCONFATT {log_id}: rate-locked {ip} "
                             f"after {config.FAIL_COUNT_TO_CONFIRM_RATELIMIT} fails")
            return err(429, "Too many requests, try again later")

        return err(status, msg)

    value = await redis.getdel(f"regconfirm:{query.code}")
    if value is None:
        c_logger.info(f"⚠️ REGCONFATT {log_id}: {query.code=} not found (expired/invalid/used)")
        return await fail(401, "The code is not valid.")

    try:
        res = json.loads(value)
    except json.JSONDecodeError:
        c_logger.warning(f"❌ REGCONFATT {log_id} failed: "
                         f"Corrupted payload for {query.code=}: {value}")
        return await fail(500, "The code has been corrupted. "
                               "Please restart the registration process")

    if not {"type", "email", "pwhash", "nickname"}.issubset(res.keys()):
        c_logger.warning(f"❌ REGCONFATT {log_id} failed: {query.code=} was malformed: {res}")
        return await fail(500, "The code has been corrupted. "
                               "Please restart the registration process")

    email = res["email"]
    nickname = res["nickname"]

    conflict = await db.users.find_one({
        "$or": [
            {"nickname": nickname},
            {"email": email},
        ]
    })

    if conflict:
        if conflict["nickname"] == nickname:
            c_logger.warning(f"❌ REGCONFATT {log_id} failed: {nickname=} is in use")
            return await fail(409, f"Nickname {nickname} is already in use")
        else:
            c_logger.warning(f"❌ REGCONFATT {log_id} failed: {email=} is in use")
            return await fail(409, f"Email {email} is already in use")

    try:
        await db.users.insert_one({
            "nickname": nickname,
            "email": email,
            "pwhash": res["pwhash"],
            "ip": ip,
            "uuid": str(uuid.uuid4()),
            "elo": 1200,
            "games_played": 0,
        })
    except DuplicateKeyError:
        c_logger.warning(f"❌ REGCONFATT {log_id} failed: {email=} or {nickname=} already taken")
        return await fail(409, "Registration failed. Please try again")

    await ensure_constant_time()

    c_logger.info(f"▶️ REGCONFATT {log_id} successful: registered {email=}|{nickname=}|{ip=}")

    redirect = f"{config.BASE_URL}/api/v1/auth/login"
    return RedirectResponse(
        url=redirect,
        status_code=303,
    )
