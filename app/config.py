from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Food Delivery Order & Analytics Management System"
    database_url: str = "postgresql+asyncpg://food_admin:food_password@localhost:5432/food_delivery"
    sync_database_url: str = "postgresql+psycopg2://food_admin:food_password@localhost:5432/food_delivery"
    tax_rate: float = 0.05
    default_delivery_fee: float = 40.0
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_async_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = value.replace("postgres://", "postgresql://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("sync_database_url", mode="before")
    @classmethod
    def normalize_sync_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = value.replace("postgres://", "postgresql://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg2://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
