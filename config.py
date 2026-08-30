"""Central application configuration.

Values are loaded from environment variables and/or a local ``.env`` file.
All settings are validated and typed by ``pydantic-settings`` so
misconfigured deployments fail fast at startup.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Telegram
    bot_token: str = ""
    admin_ids: str = ""

    # Storage
    database_path: str = "kodli.db"

    # Anti-flood tuning
    min_message_interval_seconds: float = 1.0
    flood_burst_window_seconds: float = 10.0
    ban_duration_by_level: dict[int, int] = {2: 30, 3: 60, 4: 120}
    permanent_ban_level: int = 5

    # Misc
    default_activity_limit: int = 10
    users_per_page: int = 5
    code_max_length: int = 12

    @property
    def admins(self) -> list[int]:
        return [
            int(part.strip())
            for part in self.admin_ids.split(",")
            if part.strip().lstrip("-").isdigit()
        ]

    def is_admin(self, telegram_id: int | None) -> bool:
        return telegram_id is not None and telegram_id in self.admins

    def validate(self) -> None:
        if not self.bot_token:
            raise ValueError(
                "BOT_TOKEN is not configured. Create a .env file from .env.example first."
            )
        if not self.admins:
            raise ValueError(
                "ADMIN_IDS is empty or invalid. Provide at least one admin "
                "Telegram id in the .env file."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.validate()
    return settings


settings = get_settings()