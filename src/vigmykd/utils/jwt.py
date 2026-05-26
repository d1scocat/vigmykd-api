import logging
import uuid

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, TypeVar

from jwt import JWT
from jwt.exceptions import JWTDecodeError, JWSDecodeError
from redis.asyncio import Redis

from vigmykd.settings import keys


class ValidationResultType(Enum):
    MALFORMED = "The submitted token is malformed"
    EXPIRED = "The submitted token has expired"
    AHEAD_OF_TIME = "The submitted token is not yet available for use"
    NO_SESSION = "There is no corresponding session"
    MISSING_FIELDS = "The submitted token is not fully filled in"


@dataclass
class ValidationResult:
    is_valid: bool
    reason: ValidationResultType | None = None
    payload: dict | None = None


async def jwt_validate_token(
    token: str,
    jwt: JWT,
    redis: Redis
) -> ValidationResult:
    try:
        payload = jwt.decode(
            token,
            keys.public_key,
            do_verify=True,
            do_time_check=False
        )
    except (JWTDecodeError, JWSDecodeError) as ex:
        return ValidationResult(is_valid=False, reason=ValidationResultType.MALFORMED)

    now = datetime.now(timezone.utc).timestamp()
    exp = payload.get("exp", None)
    if not exp:
        return ValidationResult(is_valid=False, reason=ValidationResultType.MISSING_FIELDS)

    if now >= exp:
        return ValidationResult(is_valid=False, reason=ValidationResultType.EXPIRED)

    nbf = payload.get("nbf")
    if nbf and now < nbf:
        return ValidationResult(is_valid=False, reason=ValidationResultType.AHEAD_OF_TIME)

    session_id = payload.get("jti", None)
    if not session_id:
        return ValidationResult(is_valid=False, reason=ValidationResultType.MISSING_FIELDS)

    session = await redis.get(f"session:{session_id}")
    if session is None:
        return ValidationResult(is_valid=False, reason=ValidationResultType.NO_SESSION)

    return ValidationResult(
        is_valid=True,
        payload=payload
    )


M = TypeVar('M')
I = TypeVar('I')
V = TypeVar('V')


def jwt_handle_result(
    result: ValidationResult,
    on_malformed: Callable[..., M],
    on_invalid: Callable[..., I],
    on_valid: Callable[..., V] | None
) -> M | I | V | dict:
    match result.reason:
        case (
            ValidationResultType.MALFORMED |
            ValidationResultType.MISSING_FIELDS
        ):
            return on_malformed()

        case (
            ValidationResultType.EXPIRED |
            ValidationResultType.AHEAD_OF_TIME |
            ValidationResultType.NO_SESSION
        ):
            return on_invalid()

        case _:
            if on_valid:
                return on_valid()
            return result.payload


async def jwt_full_flow(
    token: str,
    jwt: JWT,
    redis: Redis,
    on_malformed: Callable[..., M],
    on_invalid: Callable[..., I],
    on_valid: Callable[..., V] | None
) -> M | I | V | dict:
    result = await jwt_validate_token(token, jwt, redis)
    return jwt_handle_result(result, on_malformed, on_invalid, on_valid)


async def jwt_full_flow_takeover(
    scheme: str,
    token: str,
    jwt: JWT,
    redis: Redis,
    logger: logging.Logger,
    log_id: uuid.UUID,
    log_prefix: str
):
    from vigmykd.utils import err, validate_creds

    creds_invalid = validate_creds(scheme, token, logger, log_id)
    if creds_invalid is not None:
        return creds_invalid

    def malformed():
        logger.warning(f"❌ {log_prefix} {log_id} FAILED: token malformed")
        return err(status_code=400, msg="Malformed token")

    def invalid():
        logger.warning(f"❌ {log_prefix} {log_id} COMPLETED: token invalid")
        return err(status_code=401, msg="Invalid token")

    token_validation = await jwt_full_flow(
        token=token,
        jwt=jwt,
        redis=redis,
        on_malformed=malformed,
        on_invalid=invalid,
        on_valid=None
    )

    return token_validation
