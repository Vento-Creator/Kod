"""Async SQLite data-access layer built on top of ``aiosqlite``.

Design notes
------------
* A **single** connection is used. This is the recommended and safe setup for
  aiogram bots because the whole application runs in one event loop and
  ``aiosqlite`` guarantees calls are serialised.
* Schema is created idempotently with ``CREATE TABLE IF NOT EXISTS``.
* All timestamps are timezone-aware UTC values stored as ISO-8601 text.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from .models import Channel, Movie, SearchLog, User

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


class Database:
    """Thin async wrapper around ``aiosqlite`` with the full CRUD surface.

    Instantiate once, call :meth:`connect` before the bot starts polling and
    :meth:`close` on shutdown.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #
    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected - call connect() first.")
        return self._conn

    async def connect(self) -> None:
        """Open the connection, enable WAL and create the schema."""
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self.conn.executescript(
            "PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;"
        )
        await self._create_schema()
        logger.info("Database ready: %s", self.path)

    async def close(self) -> None:
        """Close the underlying connection (idempotent)."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def _create_schema(self) -> None:
        """Create tables and indexes when they do not exist yet."""
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id   INTEGER NOT NULL UNIQUE,
                username      TEXT,
                full_name     TEXT,
                is_blocked    INTEGER NOT NULL DEFAULT 0,
                warning_count INTEGER NOT NULL DEFAULT 0,
                ban_until     TEXT,
                created_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS movies (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                code       TEXT NOT NULL UNIQUE,
                file_id    TEXT NOT NULL,
                file_type  TEXT NOT NULL DEFAULT 'video',
                caption    TEXT,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS logs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                searched_code TEXT NOT NULL,
                timestamp     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS channels (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id   TEXT NOT NULL UNIQUE,
                channel_url  TEXT NOT NULL,
                channel_name TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_movies_code ON movies(code);
            """
        )
        await self.conn.commit()

    # ------------------------------------------------------------------ #
    # Row mappers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)

    def _user_from_row(self, row: aiosqlite.Row) -> User:
        return User(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"],
            full_name=row["full_name"],
            is_blocked=bool(row["is_blocked"]),
            warning_count=row["warning_count"],
            ban_until=self._parse_dt(row["ban_until"]),
            created_at=self._parse_dt(row["created_at"]),
        )

    def _movie_from_row(self, row: aiosqlite.Row) -> Movie:
        return Movie(
            id=row["id"],
            code=row["code"],
            file_id=row["file_id"],
            file_type=row["file_type"],
            caption=row["caption"],
            is_deleted=bool(row["is_deleted"]),
            created_at=self._parse_dt(row["created_at"]),
        )

    def _log_from_row(self, row: aiosqlite.Row) -> SearchLog:
        return SearchLog(
            id=row["id"],
            user_id=row["user_id"],
            searched_code=row["searched_code"],
            timestamp=self._parse_dt(row["timestamp"]),
        )

    def _channel_from_row(self, row: aiosqlite.Row) -> Channel:
        return Channel(
            id=row["id"],
            channel_id=row["channel_id"],
            channel_url=row["channel_url"],
            channel_name=row["channel_name"],
        )

    # ------------------------------------------------------------------ #
    # users
    # ------------------------------------------------------------------ #
    async def get_user(self, telegram_id: int) -> User | None:
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        return self._user_from_row(row) if row else None

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
    ) -> User:
        """Return the user row, creating it on first contact.

        The username / full name are refreshed every time so the admin
        panel always shows up-to-date info.
        """
        user = await self.get_user(telegram_id)
        if user is not None:
            if (username is not None and user.username != username) or (
                full_name is not None and user.full_name != full_name
            ):
                await self.conn.execute(
                    "UPDATE users SET username = ?, full_name = ? "
                    "WHERE telegram_id = ?",
                    (username, full_name, telegram_id),
                )
                await self.conn.commit()
            return await self.get_user(telegram_id)  # re-fetch freshest row

        await self.conn.execute(
            "INSERT INTO users (telegram_id, username, full_name, created_at) "
            "VALUES (?, ?, ?, ?)",
            (telegram_id, username, full_name, utcnow().isoformat()),
        )
        await self.conn.commit()
        user = await self.get_user(telegram_id)
        assert user is not None  # just inserted
        return user

    async def list_users(self, offset: int = 0, limit: int = 5) -> list[User]:
        """Fetch a page of users ordered by registration time (newest first)."""
        cursor = await self.conn.execute(
            "SELECT * FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [self._user_from_row(row) for row in rows]

    async def count_users(self) -> int:
        cursor = await self.conn.execute("SELECT COUNT(*) AS n FROM users")
        row = await cursor.fetchone()
        return int(row["n"]) if row else 0

    async def get_active_users(self) -> list[User]:
        """All users that are neither permanently blocked nor temp-banned."""
        now = utcnow().isoformat()
        cursor = await self.conn.execute(
            "SELECT * FROM users "
            "WHERE is_blocked = 0 "
            "AND (ban_until IS NULL OR ban_until <= ?) "
            "ORDER BY id ASC",
            (now,),
        )
        rows = await cursor.fetchall()
        return [self._user_from_row(row) for row in rows]

    async def find_user_by_identifier(self, identifier: str) -> User | None:
        """Look up a user by numeric Telegram id or ``username`` / ``@username``."""
        identifier = identifier.strip()
        if identifier.isdigit() or (
            identifier.startswith("-") and identifier[1:].isdigit()
        ):
            return await self.get_user(int(identifier))
        username = identifier.lstrip("@").lower()
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE lower(username) = ?", (username,)
        )
        row = await cursor.fetchone()
        return self._user_from_row(row) if row else None

    async def set_user_blocked(self, telegram_id: int, blocked: bool) -> None:
        """Block (permanent) or unblock a user; unblocking also resets bans."""
        if blocked:
            await self.conn.execute(
                "UPDATE users SET is_blocked = 1, ban_until = NULL "
                "WHERE telegram_id = ?",
                (telegram_id,),
            )
        else:
            await self.conn.execute(
                "UPDATE users SET is_blocked = 0, ban_until = NULL, "
                "warning_count = 0 WHERE telegram_id = ?",
                (telegram_id,),
            )
        await self.conn.commit()

    async def set_user_temp_ban(
        self, telegram_id: int, ban_until: datetime, warning_count: int
    ) -> None:
        """Apply a temporary ban with the given level metadata."""
        await self.conn.execute(
            "UPDATE users SET ban_until = ?, warning_count = ?, is_blocked = 0 "
            "WHERE telegram_id = ?",
            (ban_until.isoformat(), warning_count, telegram_id),
        )
        await self.conn.commit()

    async def ban_user_permanently(
        self, telegram_id: int, warning_count: int
    ) -> None:
        """Permanent automatic ban (is_blocked = 1)."""
        await self.conn.execute(
            "UPDATE users SET is_blocked = 1, ban_until = NULL, "
            "warning_count = ? WHERE telegram_id = ?",
            (warning_count, telegram_id),
        )
        await self.conn.commit()

    # ------------------------------------------------------------------ #
    # movies
    # ------------------------------------------------------------------ #
    async def add_movie(
        self,
        code: str,
        file_id: str,
        file_type: str = "video",
        caption: str | None = None,
    ) -> Movie:
        """Insert a new movie. Raises ``IntegrityError`` on code collision."""
        await self.conn.execute(
            "INSERT INTO movies (code, file_id, file_type, caption, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (code, file_id, file_type, caption, utcnow().isoformat()),
        )
        await self.conn.commit()
        movie = await self.get_movie_by_code(code)
        assert movie is not None
        return movie

    async def get_movie_by_code(
        self, code: str, include_deleted: bool = False
    ) -> Movie | None:
        """Fetch a movie by its (unique) numeric code."""
        query = "SELECT * FROM movies WHERE code = ?"
        if not include_deleted:
            query += " AND is_deleted = 0"
        cursor = await self.conn.execute(query, (code,))
        row = await cursor.fetchone()
        return self._movie_from_row(row) if row else None

    async def get_movie_by_id(self, movie_id: int) -> Movie | None:
        cursor = await self.conn.execute(
            "SELECT * FROM movies WHERE id = ?", (movie_id,)
        )
        row = await cursor.fetchone()
        return self._movie_from_row(row) if row else None

    async def code_exists(
        self, code: str, exclude_movie_id: int | None = None
    ) -> bool:
        """Check for code collisions, optionally ignoring a given movie row."""
        if exclude_movie_id is None:
            cursor = await self.conn.execute(
                "SELECT 1 FROM movies WHERE code = ?", (code,)
            )
        else:
            cursor = await self.conn.execute(
                "SELECT 1 FROM movies WHERE code = ? AND id != ?",
                (code, exclude_movie_id),
            )
        return await cursor.fetchone() is not None

    async def update_movie(self, movie_id: int, **fields: Any) -> None:
        """Update arbitrary whitelisted columns of a movie row."""
        allowed = {"code", "file_id", "file_type", "caption", "is_deleted"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(
                f"Unknown movie fields: {', '.join(sorted(unknown))}"
            )
        if not fields:
            return
        assignments = ", ".join(f"{column} = ?" for column in fields)
        values = list(fields.values()) + [movie_id]
        await self.conn.execute(
            f"UPDATE movies SET {assignments} WHERE id = ?", values
        )
        await self.conn.commit()

    async def update_movie_media(
        self, movie_id: int, file_id: str, file_type: str
    ) -> None:
        """Update only the media file (file_id and file_type) of a movie."""
        await self.update_movie(movie_id, file_id=file_id, file_type=file_type)

    async def soft_delete_movie(self, movie_id: int) -> None:
        """Hide a movie from the user search flow (soft delete)."""
        await self.update_movie(movie_id, is_deleted=1)

    async def restore_movie(self, movie_id: int) -> None:
        """Un-hide a previously soft-deleted movie (restore)."""
        await self.update_movie(movie_id, is_deleted=0)

    async def hard_delete_movie(self, movie_id: int) -> None:
        """Permanently remove a movie row from the database."""
        await self.conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        await self.conn.commit()

    async def count_movies(self, include_deleted: bool = False) -> int:
        if include_deleted:
            cursor = await self.conn.execute(
                "SELECT COUNT(*) AS n FROM movies"
            )
        else:
            cursor = await self.conn.execute(
                "SELECT COUNT(*) AS n FROM movies WHERE is_deleted = 0"
            )
        row = await cursor.fetchone()
        return int(row["n"]) if row else 0

    async def list_movies(
        self,
        offset: int = 0,
        limit: int = 10,
        include_deleted: bool = False,
    ) -> list[Movie]:
        """Fetch a page of movies (newest first) for admin browsing."""
        query = "SELECT * FROM movies"
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        cursor = await self.conn.execute(query, (limit, offset))
        rows = await cursor.fetchall()
        return [self._movie_from_row(row) for row in rows]

    # ------------------------------------------------------------------ #
    # logs (search history)
    # ------------------------------------------------------------------ #
    async def add_log(self, user_id: int, searched_code: str) -> None:
        await self.conn.execute(
            "INSERT INTO logs (user_id, searched_code, timestamp) "
            "VALUES (?, ?, ?)",
            (user_id, searched_code, utcnow().isoformat()),
        )
        await self.conn.commit()

    async def get_recent_logs(
        self, user_id: int, limit: int = 10
    ) -> list[SearchLog]:
        cursor = await self.conn.execute(
            "SELECT * FROM logs WHERE user_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        logs = [self._log_from_row(row) for row in rows]
        logs.reverse()  # oldest -> newest for a readable timeline
        return logs

    async def count_logs(self) -> int:
        cursor = await self.conn.execute("SELECT COUNT(*) AS n FROM logs")
        row = await cursor.fetchone()
        return int(row["n"]) if row else 0

    # ------------------------------------------------------------------ #
    # channels (force-subscribe list)
    # ------------------------------------------------------------------ #
    async def add_channel(
        self, channel_id: str, channel_url: str, channel_name: str
    ) -> Channel:
        """Insert a required channel and return it (raises on duplicate id)."""
        await self.conn.execute(
            "INSERT INTO channels (channel_id, channel_url, channel_name) "
            "VALUES (?, ?, ?)",
            (channel_id, channel_url, channel_name),
        )
        await self.conn.commit()
        channel = await self.get_channel(channel_id)
        assert channel is not None  # just inserted
        return channel

    async def get_channel(self, channel_id: str) -> Channel | None:
        cursor = await self.conn.execute(
            "SELECT * FROM channels WHERE channel_id = ?", (channel_id,)
        )
        row = await cursor.fetchone()
        return self._channel_from_row(row) if row else None

    async def list_channels(self) -> list[Channel]:
        """All required channels ordered by insertion time (oldest first)."""
        cursor = await self.conn.execute("SELECT * FROM channels ORDER BY id ASC")
        rows = await cursor.fetchall()
        return [self._channel_from_row(row) for row in rows]

    async def delete_channel(self, channel_id: str) -> None:
        await self.conn.execute(
            "DELETE FROM channels WHERE channel_id = ?", (channel_id,)
        )
        await self.conn.commit()

    async def count_channels(self) -> int:
        cursor = await self.conn.execute("SELECT COUNT(*) AS n FROM channels")
        row = await cursor.fetchone()
        return int(row["n"]) if row else 0

    # ------------------------------------------------------------------ #
    # statistics (admin dashboard)
    # ------------------------------------------------------------------ #
    async def stats(self) -> dict[str, int]:
        """Aggregated counters used by the admin stats screen."""
        return {
            "users": await self.count_users(),
            "movies": await self.count_movies(include_deleted=True),
            "active_movies": await self.count_movies(),
            "searches": await self.count_logs(),
        }