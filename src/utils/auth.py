import logging
import uuid

from utils import err

def validate_creds(scheme: str, token: str, logger: logging.Logger, log_id: uuid.UUID):
    if not token or scheme != "Bearer":
        logger.warning(f"❌ VALIDATION {log_id} FAILED: no Authorization: Bearer header submitted")
        return err(status_code=400, msg=f"Please submit a token as a Bearer authorization header")
    return None
