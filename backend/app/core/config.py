from functools import cached_property
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SwagMonitor"
    api_prefix: str = "/api"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://monitor:monitor@db:5432/monitoringswagbot"
    alembic_database_url: str = "postgresql+psycopg://monitor:monitor@db:5432/monitoringswagbot"

    allowed_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost",
        ]
    )

    scheduler_enabled: bool = True
    scheduler_tick_seconds: int = 30
    run_initial_checks: bool = True

    ping_attempts: int = 4
    ping_timeout_seconds: int = 1
    default_check_interval_seconds: int = 60
    default_consecutive_alert_threshold: int = 3
    http_timeout_seconds: int = 5
    ssl_warning_days: int = 21

    telegram_bot_token: str = ""
    telegram_admin_chat_ids: str = ""

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "false", "0", "off", "no"}:
                return False
            if normalized in {"debug", "development", "dev", "true", "1", "on", "yes"}:
                return True
        return value

    @cached_property
    def admin_chat_ids(self) -> list[int]:
        chat_ids: list[int] = []
        for raw_item in self.telegram_admin_chat_ids.split(","):
            item = raw_item.strip()
            if not item:
                continue
            try:
                chat_ids.append(int(item))
            except ValueError:
                continue
        return chat_ids


settings = Settings()
