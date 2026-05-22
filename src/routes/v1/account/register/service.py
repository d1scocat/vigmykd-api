import json
import httpx
import logging
import uuid

from email_validator import validate_email, EmailNotValidError
from fastapi import Depends
from fastapi.responses import RedirectResponse

import config

from dependencies import get_db, get_mailer, get_redis
from routes.v1.account.register import models
from services.db import Database
from services.mailer import Mailer, PreaggregatedMailer
from services.redis import RedisService
from utils import err, pwd_ok, pwd_is_pwned, name_ok


logger = logging.getLogger("account.register")


async def register(
    query: models.RegisterQuery,
    db: Database = Depends(get_db),
    mailer: Mailer = Depends(get_mailer),
    redis: RedisService = Depends(get_redis),
):
    log_id = uuid.uuid4()
    logger.info(f"▶️ REGATT {log_id}: email={query.email}, nickname={query.nickname}")

    if not query.agree_with_policies:
        logger.warning(f"❌ REGATT {log_id} failed: query.agree_with_policies=False")
        return err(400, "You must agree to the policies in order to register")
    
    if not name_ok(query.nickname):
        logger.warning(f"❌ REGATT {log_id} failed: {query.nickname=} fails checks")
        return err(400, f"The nickname {query.nickname} does not match the validity criteria")
    
    conflict = await db.users.find_one({
        "$or": [
            {"nickname": query.nickname},
            {"email": query.email},
        ]
    })

    if conflict:
        if conflict["nickname"] == query.nickname:
            logger.warning(f"❌ REGATT {log_id} failed: {query.nickname=} is in use")
            return err(409, f"Nickname {query.nickname} is already in use")
        else:
            logger.warning(f"❌ REGATT {log_id} failed: {query.email=} is in use")
            return err(409, f"Email {query.email} is already in use")
    
    try:
        _ = validate_email(query.email, check_deliverability=False)
    except EmailNotValidError:
        logger.warning(f"❌ REGATT {log_id} failed: {query.email=} is invalid")
        return err(400, f"The email {query.email} is invalid or unreachable")
    
    if not pwd_ok(query.password):
        logger.warning(f"❌ REGATT {log_id} failed: password fails checks")
        return err(400, "Your password does not match the validity criteria")
    
    try:
        if await pwd_is_pwned(query.password):
            logger.warning(f"❌ REGATT {log_id} failed: password is compromised")
            return err(400, "This password is compromised and should not be used")
    except httpx.RequestError:
        logger.warning(f"❌ REGATT {log_id}: password pwn checker inaccessible"
                       ", will proceed with registration", exc_info=True)
        # return err(500, "Could not check for password presence in data breaches")
    
    reg_confirm_code = str(uuid.uuid4())
    await redis.redis.setex(
        f"confirm:{reg_confirm_code}",
        config.REG_CONFIRM_CODE_TTL,
        json.dumps({"type": "reg", "email": query.email, "nickname": query.nickname})
    )

    if not await PreaggregatedMailer.send_reg_confirmation(
        mailer=mailer,
        receiver=query.email,
        code=reg_confirm_code
    ):
        logger.error(f"❌ REGATT {log_id}: Failed to send confirmation email to {query.email}")
        await redis.redis.delete(f"confirm:{reg_confirm_code}")
        return err(500, "Could not send the registration confirmation email, try again")

    redirect = f"{config.BASE_URL}/api/v1/account/register/confirm"
    return RedirectResponse(
        url=redirect,
        status_code=303,
    )
