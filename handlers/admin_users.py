"""Admin user-management: list, block/unblock, activity logs and broadcast."""
from __future__ import annotations

import html
import logging
from math import ceil

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from database import Database
from database.models import User
from handlers.admin_filter import AdminFilter
from handlers.states import BroadcastStates, UserAdminStates
from keyboards.admin_inline import users_pagination_keyboard
from keyboards.reply import (
    ADMIN_BROADCAST_BTN,
    ADMIN_USERS_BTN,
    cancel_keyboard,
)
from services.broadcaster import broadcast
from utils import texts

logger = logging.getLogger(__name__)

router = Router(name="admin_users")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


def format_user_line(user: User, index: int) -> str:
    badge = "🚫 bloklangan" if user.is_blocked else "✅ faol"
    return texts.USER_LINE.format(
        index=index,
        name=texts.esc(user.display_name),
        tgid=user.telegram_id,
        badge=badge,
        warnings=user.warning_count,
    )


async def render_user_listing(
    target, db: Database, page: int, edit: bool = False
) -> None:
    """Render one page of the user list (used by buttons and callbacks)."""
    per_page = settings.users_per_page
    total = await db.count_users()
    total_pages = max(1, ceil(total / per_page))
    page = min(max(1, page), total_pages)

    users = await db.list_users(offset=(page - 1) * per_page, limit=per_page)
    if users:
        lines = [
            format_user_line(u, (page - 1) * per_page + i)
            for i, u in enumerate(users, start=1)
        ]
        text = texts.USERS_HEADER + "\n\n".join(lines)
    else:
        text = texts.USERS_EMPTY

    markup = users_pagination_keyboard(users, total_pages, page)
    if edit:
        await target.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


@router.message(F.text == ADMIN_USERS_BTN)
async def on_users_start(message: Message, db: Database, state: FSMContext) -> None:
    await state.clear()
    await render_user_listing(message, db, page=1, edit=False)


@router.callback_query(F.data.startswith("users_page:"))
async def on_users_page(callback: CallbackQuery, db: Database) -> None:
    page = int(callback.data.split(":", 1)[1])
    await callback.answer()
    if callback.message is None:
        return
    await render_user_listing(callback.message, db, page=page, edit=True)


@router.callback_query(F.data.startswith("user_block:"))
async def on_user_block(callback: CallbackQuery, db: Database) -> None:
    telegram_id = int(callback.data.split(":", 1)[1])
    await db.set_user_blocked(telegram_id, blocked=True)
    await callback.answer("Foydalanuvchi bloklandi 🔒")
    await _refresh_page(callback, db)


@router.callback_query(F.data.startswith("user_unblock:"))
async def on_user_unblock(callback: CallbackQuery, db: Database) -> None:
    telegram_id = int(callback.data.split(":", 1)[1])
    await db.set_user_blocked(telegram_id, blocked=False)
    await callback.answer("Blokdan chiqarildi 🔓")
    await _refresh_page(callback, db)


async def _refresh_page(callback: CallbackQuery, db: Database) -> None:
    """Refresh the last user page after a block/unblock action."""
    if callback.message is None:
        return
    try:
        page = _current_page_from_keyboard(callback.message)
    except Exception:
        page = 1
    await render_user_listing(callback.message, db, page=page, edit=True)


def _current_page_from_keyboard(message: Message) -> int:
    """Best-effort: guess the shown page from the 'X / N' button label."""
    markup = message.reply_markup
    if markup is None:
        return 1
    for row in markup.inline_keyboard:
        for button in row:
            if button.callback_data == "noop" and "/" in button.text:
                return int(button.text.split("/")[0].strip())
    return 1


@router.callback_query(F.data.startswith("user_activity:"))
async def on_user_activity(callback: CallbackQuery, db: Database) -> None:
    telegram_id = int(callback.data.split(":", 1)[1])
    user = await db.get_user(telegram_id)
    if user is None:
        await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return
    await callback.answer()
    if callback.message is None:
        return
    await _render_user_activity(callback.message, user, db, edit=True)


def _activity_lines(logs) -> list[str]:
    lines: list[str] = []
    for log in logs:
        ts = log.timestamp.strftime("%m-%d %H:%M") if log.timestamp else "?"
        lines.append(
            f"<code>{ts}</code>  ->  kod <code>{html.escape(log.searched_code)}</code>"
        )
    if not lines:
        lines.append("<i>Hali so'rov yo'q.</i>")
    return lines


async def _render_user_activity(target, user: User, db: Database, edit: bool = False) -> None:
    logs = await db.get_recent_logs(user.id, limit=settings.default_activity_limit)
    lines = _activity_lines(logs)
    text = texts.USER_ACTIVITY_HEADER.format(
        name=texts.esc(user.display_name), tgid=user.telegram_id, lines="\n".join(lines)
    )
    markup = users_pagination_keyboard([user], 1, 1)
    if edit:
        await target.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


@router.callback_query(F.data == "user_find")
async def on_user_find_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(UserAdminStates.waiting_identifier)
    await callback.answer()
    if callback.message is None:
        return
    await callback.message.edit_text(texts.USER_FIND_PROMPT, reply_markup=cancel_keyboard())


@router.message(UserAdminStates.waiting_identifier)
async def on_user_find(message: Message, state: FSMContext, db: Database) -> None:
    identifier = (message.text or "").strip()
    user = await db.find_user_by_identifier(identifier) if identifier else None
    if user is None:
        await message.answer(
            texts.USER_FIND_NOT_FOUND.format(identifier=texts.esc(identifier)),
            reply_markup=cancel_keyboard(),
        )
        return
    await state.clear()
    await _render_user_activity(message, user, db, edit=False)


# ────────────────────────────────────────────────────────────────────── #
# Broadcast
# ────────────────────────────────────────────────────────────────────── #
@router.message(F.text == ADMIN_BROADCAST_BTN)
async def on_broadcast_start(message: Message, state: FSMContext) -> None:
    await state.set_state(BroadcastStates.waiting_text)
    await message.answer(texts.BROADCAST_START, reply_markup=cancel_keyboard())


@router.message(BroadcastStates.waiting_text, F.text)
async def on_broadcast_text(message: Message, state: FSMContext, db: Database) -> None:
    if not message.text:
        return
    text = html.escape(message.text).strip()
    if not text:
        await message.answer(texts.BROADCAST_EMPTY)
        return

    await state.clear()
    await message.answer(texts.BROADCAST_SENDING)

    result = await broadcast(db, bot=message.bot, text=text)
    await message.answer(
        texts.BROADCAST_DONE.format(
            total=result.total, sent=result.sent,
            failed=result.failed, newly_blocked=result.newly_blocked,
        ),
    )