"""Application configuration settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/malong_management",
        description="PostgreSQL connection URL",
    )
    echo: bool = Field(default=False, description="Enable SQL echo for debugging")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")


class FeishuSettings(BaseSettings):
    """Feishu API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="FEISHU_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_id: str = Field(..., description="Feishu app ID")
    app_secret: str = Field(..., description="Feishu app secret")
    base_url: str = Field(
        default="https://open.feishu.cn/open-apis",
        description="Feishu API base URL",
    )
    token_refresh_buffer_minutes: int = Field(
        default=10,
        description="Minutes before expiry to refresh token",
    )
    rate_limit_delay_ms: int = Field(
        default=100,
        description="Delay between API calls in milliseconds",
    )


class AppSettings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    name: str = Field(default="管理助手", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(
        default="json",
        description="Log format (json or console)",
    )

    # Sync settings
    sync_interval_hours: int = Field(
        default=6,
        description="Organization sync interval in hours",
    )

    # Database
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # Feishu
    feishu: FeishuSettings = Field(default_factory=FeishuSettings)


@lru_cache
def get_settings() -> AppSettings:
    """Get cached application settings.

    Returns:
        AppSettings instance with values from environment variables.
    """
    return AppSettings()


settings = get_settings()
