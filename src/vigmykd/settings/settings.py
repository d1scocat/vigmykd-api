import dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


dotenv.load_dotenv()


class _Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=True,
    )

    BASE_URL: str = Field(...)

    REDIS_URL: str = Field(...)
    SMTP_HOST: str = Field(...)
    SMTP_PORT: str = Field(...)
    SMTP_USER: str = Field(...)
    SMTP_PASS: str = Field(...)

    DB_URL: str = Field(...)
    DB_NAME: str = Field(...)

    REG_CONFIRM_CODE_TTL: int = Field(...)
    DEL_CONFIRM_CODE_TTL: int = Field(...)

    HEALTHCHECK: int = Field(...)

    REDIS_HEALTHCHECK_TIMEOUT: int = Field(...)
    DB_HEALTHCHECK_TIMEOUT: int = Field(...)
    SMTP_HEALTHCHECK_TIMEOUT: int = Field(...)
    GLOBAL_HEALTHCHECK_TIMEOUT: int = Field(...)

    MIN_CONFIRM_EXEC_TIME: float = Field(...)

    FAIL_COUNT_TO_CONFIRM_RATELIMIT: int = Field(...)
    CONFIRM_RATELIMIT_SECONDS: int = Field(...)

    ARGON_TIME_COST: int = Field(...)
    ARGON_MEMORY_COST: int = Field(...)
    ARGON_PARALLELISM: int = Field(...)
    ARGON_HASH_LENGTH: int = Field(...)

    SESSION_ID_LENGTH: int = Field(...)
    SESSION_LENGTH_DAYS: int = Field(...)

    PUBLIC_KEY_PATH: str = Field(...)
    PRIVATE_KEY_PATH: str = Field(...)

    REDIS_SESSION_SYNC_PERIOD: int = Field(...)
    MONGO_SESSION_EXPIRY_SYNC_PERIOD: int = Field(...)

    DELETED_ACCOUNTS_TTL_DAYS: int = Field(...)


config = _Settings()
