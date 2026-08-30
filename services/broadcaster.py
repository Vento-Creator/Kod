"""Broadcast service - sends a message to every active user.

Handles the most common Telegram API errors gracefully:
* user blocked the bot  -> user marked as blocked in the database,
* a group chat migrated -> message re-sent to the new chat id,
* Telegram rate limits  -> waits and retries once,
* any other API error   -> counted as failed but never fatal.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Literal

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramMigrateToChat,
    TelegramRetryAfter,
)

from database import Database
from utils import texts

logger = logging.getLogger(__name__)

DeliveryStatus = Literal["sent", "blocked", "failed"]


@dataclass(slots=True)
class BroadcastResult:
    """Outcome summary shown to the admin after a broadcast."""

    total: int
    sent: int
    failed: int
    newly_blocked: int = 0

    @property
    def preview(self) -> str:
        """Compact human readable summary used in callback messages."""
        return texts.BROADCAST_DONE.format(
            total=self.total,
            sent=self.sent,
            failed=self.failed,
            newly_blocked=self.newly_blocked,
        )


async def _deliver(bot: Bot, user_id: int, text: str) -> DeliveryStatus:
    """Try to send one message; return its outcome."""
    for attempt in range(2):
        try:
            await bot.send_message(chat_id=user_id, text=text)
            return "sent"
        except TelegramRetryAfter as exc:
            # Telegram asked to slow down - wait the required period and retry.
            await asyncio.sleep(exc.retry_after + 1)
            if attempt:
                break
        except TelegramForbiddenError:
            # The user blocked the bot.
            return "blocked"
        except TelegramMigrateToChat as exc:
            # A migrated group chat - deliver to the new chat id.
            try:
                await bot.send_message(chat_id=exc.new_chat_id, text=text)
                return "sent"
            except TelegramAPIError:
                return "failed"
        except TelegramAPIError as exc:
            logger.debug("Broadcast failure to %s: %s", user_id, exc)
            return "failed"
    return "failed"


async def broadcast(db: Database, bot: Bot, text: str) -> BroadcastResult:
    """Send ``text`` to every active (non-blocked / non-temp-banned) user.

    Users that have the bot blocked are automatically flagged in the database
    so later broadcasts skip them.
    """
    users = await db.get_active_users()
    result = BroadcastResult(total=len(users))

    for user in users:
        status = await _deliver(bot, user.telegram_id, text)
        if status == "sent":
            result.sent += 1
        else:
            result.failed += 1
            if status == "blocked":
                await db.set_user_blocked(user.telegram_id, blocked=True)
                result.newly_blocked += 1

    logger.info(
        "Broadcast finished: sent=%d failed=%d total=%d",
        result.sent,
        result.failed,
        result.total,
    )
    return result