"""User flow: requesting a movie by its numeric code."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from database import Database
from keyboards.admin_inline import search_results_keyboard, subscription_required_keyboard
from services.movies import MovieService
from services.subscription import format_channels, get_subscription_status
from services.users import register_user
from utils import texts, send_media

logger = logging.getLogger(__name__)

router = Router(name="user")


@router.message(
    StateFilter(None),
    F.chat.type == "private",
    F.text.isdigit(),  # strict: ONLY pure numeric codes ever reach this handler
)
async def on_code_search(message: Message, db: Database) -> None:
    """Handle a plain numeric message: forward the matching movie.

    The ``F.text.isdigit()`` filter guarantees this handler never claims
    admin Reply-Keyboard presses (their labels always contain non-digit
    emoji/text, e.g. "⬆️ Yuklash"), so there is no collision with the
    admin button handlers.
    """
    user = await register_user(
        db,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    # Force-subscribe guard: regular users must be subscribed to every
    # required channel before the search is allowed. Admins bypass it.
    if not settings.is_admin(message.from_user.id):
        missing, unverifiable = await get_subscription_status(
            bot=message.bot, db=db, user_id=message.from_user.id
        )
        if missing or unverifiable:
            blocked = missing + unverifiable
            notice = texts.SUB_REQUIRED.format(
                channels=format_channels(blocked)
            )
            if unverifiable:
                # The bot could not verify some channel(s) - tell the user
                # this is a bot-rights/id problem, not a real subscription.
                notice += "\n\n" + texts.SUB_CHANNEL_UNCHECKABLE.format(
                    channels=format_channels(unverifiable)
                )
            await message.answer(
                notice,
                reply_markup=subscription_required_keyboard(blocked),
            )
            return

    code: str = message.text.strip()
    normalized = str(int(code))  # "007" and "7" refer to the same movie

    await db.add_log(user_id=user.id, searched_code=normalized)

    movie = await MovieService(db).find(normalized)
    if movie is None:
        await message.answer(
            texts.NOT_FOUND_TEXT.format(code=texts.esc(code)),
            reply_markup=search_results_keyboard(),
        )
        return

    ok = await send_media(
        bot=message.bot,
        chat_id=message.chat.id,
        movie=movie,
        reply_markup=search_results_keyboard(),
    )
    if not ok:
        await message.answer(
            texts.FAILED_MEDIA_TEXT.format(code=texts.esc(code)),
            reply_markup=search_results_keyboard(),
        )


@router.message(StateFilter(None), F.chat.type == "private")
async def generic_hint(message: Message) -> None:
    """Catch-all guidance for non-numeric user messages.

    The strict numeric filter above guarantees only pure digits ever reach
    the search flow; invalid input here only shows a gentle hint.

    Admin Reply-Keyboard presses are handled by the admin routers, which are
    registered earlier in ``main.py`` and therefore consume the update first.
    As a second safety net we also ignore messages sent by admins here, so
    pressing a button (or typing anything non-numeric) never produces the
    confusing "faqat raqamlardan iborat kod" prompt for them.
    """
    if not message.text or message.text.startswith("/"):
        return
    # Admin actions (Reply-Keyboard buttons) belong to the admin routers.
    if settings.is_admin(message.from_user.id):
        return
    await message.answer(texts.INVALID_CODE_TEXT)