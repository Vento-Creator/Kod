"""Force-subscribe (majburiy obuna) helpers.

The service resolves a user's membership against every required channel
stored in the database using ``bot.get_chat_member``.

Membership is considered valid when the user's status is one of:
``member``, ``administrator`` or ``creator`` (see :data:`VALID_STATUSES`).
Any other status - or a Telegram API error (e.g. the user never joined) -
counts as *not subscribed*.
"""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from database import Database
from database.models import Channel
from utils import texts

logger = logging.getLogger(__name__)

#: Statuses returned by ``get_chat_member`` that count as "subscribed".
VALID_STATUSES = frozenset({"member", "administrator", "creator"})


async def check_channel_subscription(
    bot: Bot, channel_id: str, user_id: int
) -> bool:
    """Return ``True`` when ``user_id`` is a valid member of ``channel_id``."""
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
    except TelegramAPIError as exc:
        # Bot cannot read the chat (not a member/admin) or the user is not in
        # it -> treat as not subscribed, the rest of the flow handles it.
        logger.debug(
            "get_chat_member(%s, %s) failed: %s", channel_id, user_id, exc
        )
        return False
    return member.status in VALID_STATUSES


async def get_missing_channels(
    bot: Bot, db: Database, user_id: int
) -> list[Channel]:
    """Return all required channels the user is not subscribed to (in order)."""
    missing: list[Channel] = []
    for channel in await db.list_channels():
        if not await check_channel_subscription(bot, channel.channel_id, user_id):
            missing.append(channel)
    return missing


async def is_subscribed(bot: Bot, db: Database, user_id: int) -> bool:
    """``True`` when the user belongs to every required channel."""
    return not await get_missing_channels(bot, db, user_id)


def format_channels(channels: list[Channel]) -> str:
    """Render the missing-channel list as HTML lines for prompt messages."""
    return "\n".join(
        f"📢 <b>{texts.esc(c.channel_name)}</b> (<code>{texts.esc(c.channel_id)}</code>)"
        for c in channels
    )