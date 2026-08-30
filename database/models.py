"""Plain dataclass models mirroring the database tables.

Using frozen/slots dataclasses keeps the models immutable, cheap and trivial
to use across the whole codebase (no ORM involved).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class User:
    """A row from the ``users`` table."""

    id: int
    telegram_id: int
    username: str | None = None
    full_name: str | None = None
    is_blocked: bool = False
    warning_count: int = 0
    ban_until: datetime | None = None
    created_at: datetime | None = None

    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        if self.username:
            return f"@{self.username}"
        return f"user-{self.telegram_id}"


@dataclass(slots=True)
class Movie:
    """A stored media item with its unique numeric code."""

    id: int
    code: str
    file_id: str
    file_type: str = "video"
    caption: str | None = None
    is_deleted: bool = False
    created_at: datetime | None = None


@dataclass(slots=True)
class SearchLog:
    """A single row from the ``logs`` table (a request made by a user)."""

    id: int
    user_id: int
    searched_code: str
    timestamp: datetime | None = None


@dataclass(slots=True)
class Channel:
    """A required-for-subscription channel row (force-subscribe list)."""

    id: int
    channel_id: str
    channel_url: str
    channel_name: str