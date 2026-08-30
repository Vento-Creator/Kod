"""Filter that only lets configured admin ids through."""
from __future__ import annotations

from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import settings


class AdminFilter(BaseFilter):
    """Accepts an event when its author is listed in ``settings.admins``."""

    async def __call__(
        self, event: Message | CallbackQuery, **kwargs: Any  # noqa: ARG002
    ) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and settings.is_admin(user.id)


class NotAdminFilter(BaseFilter):
    """Accepts a private-chat event from a NON-admin user."""

    async def __call__(
        self, event: Message | CallbackQuery, **kwargs: Any  # noqa: ARG002
    ) -> bool:
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        return not settings.is_admin(user.id)