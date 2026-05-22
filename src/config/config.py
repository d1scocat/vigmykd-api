import os
import dotenv


dotenv.load_dotenv()


BASE_URL=os.getenv("BASE_URL")

# The choice to have a non-integer fallback for os.getenv is very intentional
# I do not want to hardcode any values and I also want to force the user (myself lol)
# to fill in every single .env field. If any one is missing, I want the program
# to fail fast instead of proceeding silently.
# Tbh I wouldn't be adding any fallbacks at all, if not for my typechecker complaining
# about me sending NoneType into int().
REG_CONFIRM_CODE_TTL = int(os.getenv("REG_CODE_TTL", ""))

HEALTHCHECK = int(os.getenv("HEALTHCHECK", ""))

REDIS_HEALTHCHECK_TIMEOUT = int(os.getenv("REDIS_HEALTHCHECK_TIMEOUT", ""))
DB_HEALTHCHECK_TIMEOUT = int(os.getenv("DB_HEALTHCHECK_TIMEOUT", ""))
SMTP_HEALTHCHECK_TIMEOUT = int(os.getenv("SMTP_HEALTHCHECK_TIMEOUT", ""))
GLOBAL_HEALTHCHECK_TIMEOUT = int(os.getenv("GLOBAL_HEALTHCHECK_TIMEOUT", ""))