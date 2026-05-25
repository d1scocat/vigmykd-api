import logging
import uuid

from jwt import JWT
from redis.asyncio import Redis

from utils import err, jwt_validate_token, validate_creds, jwt_handle_result


logger = logging.getLogger("auth.diagnostic.validate_token")


async def validate(
    scheme: str,
    token: str,
    redis: Redis,
    jwt: JWT
):
    log_id = uuid.uuid4()
    logger.info(f"▶️ VALIDATION {log_id}")

    creds_invalid = validate_creds(scheme, token, logger, log_id)
    if creds_invalid is not None:
        return creds_invalid

    result = await jwt_validate_token(
        token=token,
        jwt=jwt,
        redis=redis
    )

    def malformed():
        logger.warning(f"❌ VALIDATION {log_id} FAILED: {result.reason.value}")
        return err(status_code=400, msg=result.reason.value)

    def invalid():
        logger.warning(f"✅ VALIDATION {log_id} COMPLETED: token invalid ({result.reason.value})")
        return {"valid": False}

    def valid():
        logger.info(f"✅ VALIDATION {log_id} COMPLETED: token valid")
        return {"valid": True}

    return jwt_handle_result(
        result=result,
        on_malformed=malformed,
        on_invalid=invalid,
        on_valid=valid
    )
