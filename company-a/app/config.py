
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    rabbitmq_url: str
    rabbitmq_queue: str

    redis_url: str
    rate_limit: str
    rate_limit_key: str

    provider_url: str


settings = Settings()
