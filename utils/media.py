"""Media helpers: extract file ids from incoming messages and replay them.

The stored ``file_id`` is bound to the bot that uploaded it, so it can be
re-sent with the matching send method later.
"""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

from database.models import Movie

logger = logging.getLogger(__name__)


async def send_media(
    bot: Bot,
    chat_id: int,
    movie: Movie,
    *,
    reply_to_message_id: int | None = None,
    disable_notification: bool = False,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """Send a stored movie to ``chat_id`` using the correct Telegram method.

    Returns ``True`` on success and ``False`` when the file_id is stale or
    the chat cannot receive media; never raises to the caller.
    """
    try:
        if movie.file_type == "video":
            await bot.send_video(
                chat_id,
                movie.file_id,
                caption=movie.caption or None,
                reply_to_message_id=reply_to_message_id,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
            )
        elif movie.file_type == "animation":
            await bot.send_animation(
                chat_id,
                movie.file_id,
                caption=movie.caption or None,
                reply_to_message_id=reply_to_message_id,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
            )
        elif movie.file_type == "audio":
            await bot.send_audio(
                chat_id,
                movie.file_id,
                caption=movie.caption or None,
                reply_to_message_id=reply_to_message_id,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
            )
        elif movie.file_type == "document":
            await bot.send_document(
                chat_id,
                movie.file_id,
                caption=movie.caption or None,
                reply_to_message_id=reply_to_message_id,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
            )
        elif movie.file_type == "voice":
            await bot.send_voice(
                chat_id,
                movie.file_id,
                caption=movie.caption or None,
                reply_to_message_id=reply_to_message_id,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
            )
        elif movie.file_type == "photo":
            await bot.send_photo(
                chat_id,
                movie.file_id,
                caption=movie.caption or None,
                reply_to_message_id=reply_to_message_id,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
            )
        else:  # unknown type - fall back to sending as a video
            await bot.send_video(
                chat_id,
                movie.file_id,
                caption=movie.caption or None,
                reply_to_message_id=reply_to_message_id,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
            )
        return True
    except TelegramBadRequest as exc:
        logger.warning(
            "Could not send media file_id=%s (%s): %s",
            movie.file_id,
            movie.file_type,
            exc,
        )
        return False


def extract_media(message: Message) -> tuple[str, str] | None:
    """Extract ``(file_id, file_type)`` from an incoming media message.

    Returns ``None`` when the message does not contain any supported media.
    """
    if message.video is not None:
        return message.video.file_id, "video"
    if message.animation is not None:
        return message.animation.file_id, "animation"
    if message.audio is not None:
        return message.audio.file_id, "audio"
    if message.document is not None:
        return message.document.file_id, "document"
    if message.voice is not None:
        return message.voice.file_id, "voice"
    if message.photo:  # a list of sizes - the last one is the highest quality
        return message.photo[-1].file_id, "photo"
    return None