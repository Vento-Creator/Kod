"""Global handler for exceptions that escape the regular routing flow."""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
)
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)

router = Router(name="errors")


@router.errors()
async def on_global_error(event: ErrorEvent) -> bool:
    """Swallow and log unhandled errors instead of crashing the poller.

    The event is consumed (returns ``True``) so aiogram does not keep
    re-delivering it.
    """
    exc = event.exception

    if isinstance(exc, TelegramForbiddenError):
        logger.info("Forbidden (user blocked the bot): %s", exc)
    elif isinstance(exc, TelegramBadRequest):
        # Most common case: a message/caption that cannot be edited or a
        # removed chat. Nothing actionable unless it repeats -> log only.
        logger.debug("Bad request handled: %s", exc)
    elif isinstance(exc, TelegramAPIError):
        logger.warning("Telegram API error: %s", exc)
    else:
        logger.exception(
            "Unhandled exception while processing an update. "
            "Update=%s",
            event.update,
        )

    return True