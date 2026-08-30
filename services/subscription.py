"""Force-subscribe (majburiy obuna) helpers.

The service resolves a user's membership against every required channel
stored in the database using ``bot.get_chat_member``.

Membership is considered valid when the user's status is one of:
``member``, ``administrator`` or ``creator`` (see :data:`VALID_STATUSES`).

IMPORTANT - three-state result
------------------------------
Telegram only lets a bot query ``getChatMember`` for arbitrary users when
the bot is an **administrator of the channel**. When the bot is not an admin
(or the stored channel id is wrong / the bot was kicked), the API returns an
error and the subscription **cannot be verified** at all. That is very
different from "the user is not subscribed" and must be surfaced to the
admin instead of falsely telling the user to subscribe.

``check_channel_subscription`` therefore returns:
* ``True``  - verified: user is a member/administrator/creator,
* ``False`` - verified: user is NOT subscribed,
* ``None``  - impossible to verify (bot rights / channel id problem).
"""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

from database import Database
from database.models import Channel
from utils import texts

logger = logging.getLogger(__name__)

#: Statuses returned by ``get_chat_member`` that count as "subscribed".
VALID_STATUSES = frozenset({"member", "administrator", "creator"})

#: Error fragments that mean "the bot itself cannot read this channel" rather
#: than "this user is not a member". With those, the check is impossible and
#: reporting a missing subscription would be a false positive.
_UNVERIFIABLE_FRAGMENTS = (
    "chat not found",
    "channel not found",
    "bot is not a member",
    "bot is not a participant",
    "bot was kicked",
    "not enough rights",
    "chat admin privileges are required",
    "method is available only for supergroups",
    "group chat was upgraded",
)


def _is_unverifiable_error(exc: TelegramAPIError) -> bool:
    """``True`` when the error means the bot cannot verify the channel at all."""
    if isinstance(exc, TelegramForbiddenError):
        return True
    if isinstance(exc, TelegramBadRequest):
        message = (getattr(exc, "message", "") or "").lower()
        return any(fragment in message for fragment in _UNVERIFIABLE_FRAGMENTS)
    return False


async def check_channel_subscription(
    bot: Bot, channel_id: str, user_id: int
) -> bool | None:
    """Return ``True``/``False`` when verifiable, or ``None`` when the bot
    cannot verify the channel (not an admin / wrong id / kicked)."""
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
    except TelegramAPIError as exc:
        if _is_unverifiable_error(exc):
            # The bot itself has no access to the channel - surface it loudly
            # so the admin fixes the bot rights / channel id instead of users
            # being flooded with a wrong "subscribe" prompt.
            logger.warning(
                "Channel %s cannot be verified for user %s (bot not admin / "
                "wrong id / kicked): %s",
                channel_id, user_id, exc,
            )
            return None
        # Any other API error (e.g. the user really is not a member) simply
        # means "not subscribed".
        logger.debug(
            "get_chat_member(%s, %s) failed: %s", channel_id, user_id, exc
        )
        return False

    status = getattr(member, "status", "")
    if status in VALID_STATUSES:
        return True
    # Users who joined but are muted/limited (e.g. by channel slow-mode or
    # admin restrictions) report status "restricted" with is_member=True -
    # they ARE subscribed and must not be blocked.
    if status == "restricted" and bool(getattr(member, "is_member", False)):
        return True
    # Log the exact status so a false "not subscribed" can be diagnosed from
    # the Railway logs (status + which channel id was actually checked).
    logger.warning(
        "User %s is NOT a member of channel %s (status=%s) - reported as missing",
        user_id, channel_id, status or "<unknown>",
    )
    return False


async def get_subscription_status(
    bot: Bot, db: Database, user_id: int
) -> tuple[list[Channel], list[Channel]]:
    """Return ``(missing, unverifiable)`` required channels.

    ``missing``      - verified as not subscribed (user really must subscribe),
    ``unverifiable`` - the bot could NOT check the channel (bot rights/id bug).
    """
    missing: list[Channel] = []
    unverifiable: list[Channel] = []
    for channel in await db.list_channels():
        result = await check_channel_subscription(
            bot, channel.channel_id, user_id
        )
        if result is False:
            missing.append(channel)
        elif result is None:
            unverifiable.append(channel)
    return missing, unverifiable


async def get_missing_channels(
    bot: Bot, db: Database, user_id: int
) -> list[Channel]:
    """All required channels the user is verified not to be subscribed to."""
    missing, _ = await get_subscription_status(bot, db, user_id)
    return missing


async def is_subscribed(bot: Bot, db: Database, user_id: int) -> bool:
    """``True`` when the user belongs to every required channel and every
    channel could be verified (unverifiable channels count as not confirmed)."""
    missing, unverifiable = await get_subscription_status(bot, db, user_id)
    return not missing and not unverifiable


def format_channels(channels: list[Channel]) -> str:
    """Render the missing-channel list as HTML lines for prompt messages."""
    return "\n".join(
        f"📢 <b>{texts.esc(c.channel_name)}</b> (<code>{texts.esc(c.channel_id)}</code>)"
        for c in channels
    )