"""Common handlers: /start, /help and the main-menu buttons."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import settings
from database import Database
from keyboards.admin_inline import subscription_required_keyboard
from keyboards.reply import (
    ADMIN_HOME_BTN,
    HOME_HELP_BTN,
    HOME_SEARCH_BTN,
    admin_main_keyboard,
    home_keyboard,
)
from services.subscription import format_channels, get_missing_channels
from services.users import register_user
from utils import texts

logger = logging.getLogger(__name__)

router = Router(name="common")

START_ADMIN = (
    "🛠️ <b>Admin panel</b>\n\n"
    "Qo'shish, qidirish yoki boshqaruv uchun menyudan foydalaning."
)
START_HOME = (
    "🏠 <b>Bosh menyu</b>\n\n"
    "Yangi qidiruv yoki boshqa harakat uchun quyidagi tugmalardan foydalaning."
)

HOME_INLINE = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔎 Kino kodini yuborish", callback_data="search_new")],
    [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="home")],
])


@router.message(CommandStart())
async def on_start(message: Message, db: Database) -> None:
    await register_user(
        db,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    if settings.is_admin(message.from_user.id):
        await message.answer(texts.PANEL_TEXT, reply_markup=admin_main_keyboard())
        return

    # Force-subscribe guard: only for regular users.
    missing = await get_missing_channels(
        bot=message.bot, db=db, user_id=message.from_user.id
    )
    if missing:
        await message.answer(
            texts.SUB_REQUIRED.format(channels=format_channels(missing)),
            reply_markup=subscription_required_keyboard(missing),
        )
        return

    await message.answer(texts.START_USER, reply_markup=home_keyboard())


@router.message(Command("help"))
async def on_help(message: Message, db: Database) -> None:
    await register_user(
        db,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(texts.HELP_TEXT)


@router.message(F.text == HOME_HELP_BTN)
async def on_help_button(message: Message, db: Database) -> None:
    await on_help(message, db)


@router.message(F.text == HOME_SEARCH_BTN)
async def on_find_button(message: Message) -> None:
    await message.answer(texts.SEARCH_PROMPT)


@router.message(F.text == ADMIN_HOME_BTN)
async def on_admin_home_button(message: Message) -> None:
    if settings.is_admin(message.from_user.id):
        await message.answer(START_ADMIN, reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "home")
async def on_home_callback(callback: CallbackQuery, db: Database) -> None:
    """Reset the conversation to the appropriate root menu (admin vs user)."""
    await register_user(
        db,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name,
    )
    await callback.answer()
    if callback.message is None:
        return
    if settings.is_admin(callback.from_user.id):
        # The persistent reply keyboard stays visible; edit_text cannot
        # apply a ReplyKeyboardMarkup, so we only swap the message text.
        await callback.message.edit_text(START_ADMIN)
    else:
        await callback.message.edit_text(START_HOME, reply_markup=HOME_INLINE)


@router.callback_query(F.data == "search_new")
async def on_search_new(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None:
        return
    await callback.message.edit_text(texts.SEARCH_PROMPT, reply_markup=HOME_INLINE)


@router.callback_query(F.data == "sub_check")
async def on_sub_check(callback: CallbackQuery, db: Database) -> None:
    """Re-verify subscription after the user pressed '✅ Tekshirish'."""
    user_id = callback.from_user.id
    await callback.answer()

    # Admins are never subject to the force-subscribe guard.
    if settings.is_admin(user_id):
        await callback.message.edit_text(START_ADMIN, reply_markup=HOME_INLINE)
        return
    if callback.message is None:
        return

    missing = await get_missing_channels(bot=callback.bot, db=db, user_id=user_id)
    if missing:
        await callback.message.edit_text(
            texts.SUB_STILL_MISSING.format(channels=format_channels(missing)),
            reply_markup=subscription_required_keyboard(missing),
        )
        return

    await callback.message.edit_text(texts.SUB_SUCCESS, reply_markup=HOME_INLINE)