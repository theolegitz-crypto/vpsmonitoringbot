from dataclasses import dataclass
from functools import cached_property
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class TelegramTarget:
    chat_id: int
    message_thread_id: int | None = None


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
    cleanup_interval_hours: int = 6

    auth_enabled: bool = True
    auth_cookie_name: str = "swagmonitor_session"
    auth_session_ttl_hours: int = 72
    auth_cookie_secure: bool = False
    auth_bootstrap_username: str = "admin"
    auth_bootstrap_password: str = ""

    ping_attempts: int = 4
    ping_timeout_seconds: int = 1
    default_check_interval_seconds: int = 60
    default_consecutive_alert_threshold: int = 3
    default_ssh_metrics_interval_seconds: int = 300
    default_speed_test_enabled: bool = False
    default_speed_test_interval_seconds: int = 21600
    ssh_scheduler_enabled: bool = True
    ssh_connect_timeout_seconds: int = 8
    ssh_command_timeout_seconds: int = 20
    ssh_speed_test_timeout_seconds: int = 180
    ssh_allow_unknown_hosts: bool = True
    ssh_credentials_key: str = ""
    speed_test_scheduler_enabled: bool = True
    http_timeout_seconds: int = 5
    ssl_warning_days: int = 21
    failure_retry_enabled: bool = True
    failure_retry_attempts: int = 1
    failure_retry_delay_seconds: int = 3
    diagnostics_enabled: bool = True
    traceroute_enabled: bool = True
    traceroute_max_hops: int = 12
    traceroute_timeout_seconds: int = 2
    check_results_retention_days: int = 30
    check_result_rollup_retention_days: int = 365
    agent_metrics_retention_days: int = 14
    container_metrics_retention_days: int = 14
    diagnostic_retention_days: int = 14
    speed_test_retention_days: int = 30
    speed_test_degradation_alert_enabled: bool = True
    speed_test_baseline_samples: int = 5
    speed_test_baseline_min_samples: int = 3
    speed_test_baseline_window_hours: int = 168
    speed_test_warning_ratio: float = 0.7
    speed_test_critical_ratio: float = 0.5
    speed_test_ping_warning_multiplier: float = 1.5
    speed_test_ping_critical_multiplier: float = 2.0
    speed_test_alert_cooldown_minutes: int = 180
    speed_test_recovery_window_hours: int = 24
    alert_events_retention_days: int = 90
    resolved_incident_retention_days: int = 90

    agent_ingest_enabled: bool = True
    agent_shared_token: str = ""

    telegram_bot_token: str = ""
    telegram_admin_chat_ids: str = ""
    telegram_allowed_chat_ids: str = ""
    telegram_allow_private_chats: bool = True

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
    def admin_chat_targets(self) -> list[TelegramTarget]:
        return self._parse_telegram_targets(self.telegram_admin_chat_ids)

    @cached_property
    def admin_chat_ids(self) -> list[int]:
        return [target.chat_id for target in self.admin_chat_targets]

    @cached_property
    def allowed_chat_targets(self) -> list[TelegramTarget]:
        return self._parse_telegram_targets(self.telegram_allowed_chat_ids)

    def _parse_telegram_targets(self, raw_value: str) -> list[TelegramTarget]:
        targets: list[TelegramTarget] = []
        for raw_item in raw_value.split(","):
            item = raw_item.strip()
            if not item:
                continue
            try:
                if ":" in item:
                    chat_raw, topic_raw = item.split(":", 1)
                    targets.append(
                        TelegramTarget(
                            chat_id=int(chat_raw.strip()),
                            message_thread_id=int(topic_raw.strip()),
                        )
                    )
                else:
                    targets.append(TelegramTarget(chat_id=int(item)))
            except ValueError:
                continue
        return targets

    def is_allowed_telegram_context(
        self,
        *,
        chat_id: int,
        message_thread_id: int | None,
        chat_type: str,
    ) -> bool:
        if chat_type == "private" and self.telegram_allow_private_chats:
            return True

        if not self.allowed_chat_targets:
            return True

        for target in self.allowed_chat_targets:
            if target.chat_id != chat_id:
                continue
            if target.message_thread_id is None:
                return True
            if target.message_thread_id == message_thread_id:
                return True
        return False


settings = Settings()
