"""Global cancellation handler.

This router is registered *first* in ``main.py`` on purpose. In aiogram 3 the
dispatcher walks routers in registration order and the first handler whose
filters match consumes the update - so the cancel handler here runs before any
state-specific handler (``UploadStates.*``, ``BroadcastStates.*``,
``ChannelStates.*``, ...) could intercept the "❌ Bekor qilish" button.

``StateFilter("*")`` matches every FSM state, so a press always clears the
active dialog no matter which step the user is on.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import settings
from keyboards.reply import (
    CANCEL_BTN,
    admin_main_keyboard,
    home_keyboard,
)
from utils import texts

router = Router(name="global_cancel")

# Cancellation triggers: the Reply-Keyboard button, the literal text, and a
# /cancel slash command. All of them work from any FSM state.
CANCEL_TRIGGERS = frozenset({CANCEL_BTN, "❌ Bekor qilish", "/cancel"})


@router.message(
    StateFilter("*"),
    F.text.in_(CANCEL_TRIGGERS),
)
async def on_cancel(message: Message, state: FSMContext) -> None:
    """Clear any active FSM state and return the user to their root menu."""
    if state is not None:
        await state.clear()
    await message.answer(
        texts.CANCELLED,
        reply_markup=(
            admin_main_keyboard()
            if settings.is_admin(message.from_user.id)
            else home_keyboard()
        ),
    )