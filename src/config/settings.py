from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str | None = Field(default=None, validation_alias="DATABASE_URL")
    POSTGRES_USER: str = "db"
    POSTGRES_PASSWORD: str = "tiger"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "PayU_db"

    JWT_SECRET_KEY: str = Field(default="", validation_alias="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    REDIS_HOST: str = Field(default="redis", validation_alias="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, validation_alias="REDIS_PORT")
    REDIS_DB: int = Field(default=0, validation_alias="REDIS_DB")

    VALIDATION_EVENTS_STREAM: str = Field(
        default="validation-events",
        validation_alias="VALIDATION_EVENTS_STREAM",
    )
    VALIDATION_EVENTS_CONSUMER_GROUP: str = Field(
        default="command-center-service",
        validation_alias="VALIDATION_EVENTS_CONSUMER_GROUP",
    )
    VALIDATION_EVENTS_CONSUMER_NAME: str = Field(
        default="command-center-worker-1",
        validation_alias="VALIDATION_EVENTS_CONSUMER_NAME",
    )
    REDIS_STREAM_BLOCK_MS: int = Field(
        default=5000,
        validation_alias="REDIS_STREAM_BLOCK_MS",
    )
    REDIS_STREAM_BATCH_SIZE: int = Field(
        default=10,
        validation_alias="REDIS_STREAM_BATCH_SIZE",
    )
    REDIS_STREAM_MAX_RETRIES: int = Field(
        default=3,
        validation_alias="REDIS_STREAM_MAX_RETRIES",
    )

    SENDGRID_API_KEY: str = Field(
        default="",
        validation_alias="SENDGRID_API_KEY",
    )
    SENDGRID_FROM_EMAIL: str = Field(
        default="",
        validation_alias="SENDGRID_FROM_EMAIL",
    )

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://"
                f"{self.POSTGRES_USER}:"
                f"{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_HOST}:"
                f"{self.POSTGRES_PORT}/"
                f"{self.POSTGRES_DB}"
            )

        return self


settings = Settings()
