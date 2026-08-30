"""Escalating anti-flood / anti-spam middleware.

Behaviour
---------
* Admins are never throttled.
* Permanently blocked users and users with an active temporary ban are
  **silently ignored** – their requests never reach handlers.
* A regular user sending a request sooner than ``min_message_interval``
  marks one flood **breach**. Messages belonging to the same burst (within
  ``flood_burst_window`` seconds) are swallowed and count as a single breach.
* Every new burst escalates the punishment:

    +----------+---------------------------------------------+
    | Breach # | Punishment                                  |
    +==========+=============================================+
    | 1        | warning message (no ban)                    |
    | 2        | 30  minutes temporary ban                   |
    | 3        | 60  minutes temporary ban                   |
    | 4        | 120 minutes temporary ban                   |
    | >= 5     | permanent automatic ban (``is_blocked=1``)  |
    +----------+---------------------------------------------+

* The current breach level is stored in ``users.warning_count`` so the
  escalation ladder survives restarts.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from config import settings
from database import Database, utcnow
from services.users import FloodPenalty, apply_flood_penalty

logger = logging.getLogger(__name__)


class AntiFloodMiddleware(BaseMiddleware):
    """Enforces the throttling and escalating-bans policy."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self._last_processed: dict[int, datetime] = {}
        self._last_breach: dict[int, datetime] = {}

    # ------------------------------------------------------------------ #
    async def __call__(
        self,
        handler,
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        # Only personal messages/callbacks are subject to throttling.
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        # Admins are always allowed.
        if settings.is_admin(user.id):
            return await handler(event, data)

        now = utcnow()

        # 1) Permanent block / active temporary ban -> auto-ignore.
        db_user = await self.db.get_user(user.id)
        if db_user is not None:
            if db_user.is_blocked:
                return None
            if db_user.ban_until is not None and db_user.ban_until > now:
                return None

        # 2) Normal rate-limit check.
        last_ok = self._last_processed.get(user.id)
        min_interval = timedelta(seconds=settings.min_message_interval_seconds)
        if last_ok is None or (now - last_ok) >= min_interval:
            self._last_processed[user.id] = now
            return await handler(event, data)

        # 3) Flood – swallow the event and escalate when appropriate.
        await self._handle_flood(event=event, user_id=user.id)
        return None

    # ------------------------------------------------------------------ #
    async def _handle_flood(self, event: Message | CallbackQuery, user_id: int) -> None:
        now = utcnow()
        window = timedelta(seconds=settings.flood_burst_window_seconds)

        last_breach_at = self._last_breach.get(user_id)
        is_new_breach = last_breach_at is None or (now - last_breach_at) > window

        if not is_new_breach:
            # Still inside the same burst – swallow without re-escalating.
            return

        self._last_breach[user_id] = now

        try:
            penalty: FloodPenalty = await apply_flood_penalty(
                db=self.db, telegram_id=user_id
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Flood penalty failed for %s: %s", user_id, exc)
            return

        logger.info(
            "Flood breach #%s for user %s -> %s",
            penalty.level,
            user_id,
            penalty.kind.value,
        )

        # Send the single punishment notice directly via the bot.
        try:
            target_chat = event.chat if isinstance(event, Message) else None
            if target_chat is None and isinstance(event, CallbackQuery) and event.message:
                target_chat = event.message.chat
            if target_chat is not None:
                await event.bot.send_message(
                    chat_id=target_chat.id,
                    text=penalty.user_message,
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Could not send flood notification: %s", exc)