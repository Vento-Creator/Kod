"""Middleware that makes the shared database available in every handler."""
from __future__ import annotations

from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from database import Database


class DatabaseMiddleware(BaseMiddleware):
    """Copy the shared :class:`Database` instance into ``data['db']``.

    Handlers simply declare ``db: Database`` in their signature and receive
    it automatically thanks to aiogram's dependency injection.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    async def __call__(
        self,
        handler,
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        data["db"] = self.db
        return await handler(event, data)