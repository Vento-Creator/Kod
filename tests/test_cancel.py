"""Behavioral test for the global cancel handler (no network required).

Run: python tests/test_cancel.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["BOT_TOKEN"] = "1111111110:TEST-TOKEN"
os.environ["ADMIN_IDS"] = "111111,222222"

from aiogram import Bot, Dispatcher, F, Router  # noqa: E402
from aiogram.fsm.context import FSMContext  # noqa: E402
from aiogram.fsm.storage.base import BaseStorage, StorageKey  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402
from aiogram.types import Chat, Message, Update, User as TgUser  # noqa: E402

from handlers.cancel import router as cancel_router  # noqa: E402
from handlers.states import BroadcastStates  # noqa: E402
from keyboards.reply import CANCEL_BTN, admin_main_keyboard  # noqa: E402

assert CANCEL_BTN == "❌ Bekor qilish", CANCEL_BTN
CANCEL_TRIGGERS = ("❌ Bekor qilish", "/cancel", CANCEL_BTN)
ADMIN_ID = 111111


class ProbeBot(Bot):
    """Records outgoing API calls instead of sending them over HTTP."""

    def __init__(self) -> None:
        super().__init__(token="1111111110:TEST-TOKEN")
        self.sent: list = []

    async def __call__(self, method, *args, **kwargs):
        self.sent.append((getattr(method, "text", None),
                          getattr(method, "reply_markup", None)))
        rt = getattr(method, "__return_type__", None)
        try:
            return rt() if rt is not None else SimpleNamespace()
        except Exception:
            return SimpleNamespace()


def make_update(text: str) -> Update:
    chat = Chat(id=ADMIN_ID, type="private")
    user = TgUser(id=ADMIN_ID, is_bot=False, first_name="Admin")
    msg = Message(
        message_id=42, date=datetime.now(timezone.utc), chat=chat,
        from_user=user, text=text,
    )
    return Update(update_id=1001, message=msg)


def key_for(bot: Bot) -> StorageKey:
    return StorageKey(user_id=ADMIN_ID, chat_id=ADMIN_ID, bot_id=bot.id)


async def set_state(bot: Bot, storage: BaseStorage, state) -> None:
    ctx = FSMContext(storage=storage, key=key_for(bot))
    await ctx.set_state(state)
    assert await storage.get_state(key_for(bot)) is not None


def make_competitor(intercepted: list[str]) -> Router:
    """A state-specific text handler that would swallow Cancel if registered first."""
    router = Router(name=f"competitor_{id(intercepted):x}")

    @router.message(BroadcastStates.waiting_text, F.text)
    async def handler(message: Message, state: FSMContext) -> None:
        intercepted.append("leaked")
        await message.answer("SHOULD NOT SEE THIS")
    return router


async def run() -> None:
    storage: BaseStorage = MemoryStorage()
    intercepted: list[str] = []

    bot = ProbeBot()
    dp = Dispatcher(storage=storage)
    dp.include_router(cancel_router)  # FIRST (the fix)
    dp.include_router(make_competitor(intercepted))  # state-specific, AFTER
    await set_state(bot, storage, BroadcastStates.waiting_text)

    for trigger in CANCEL_TRIGGERS:
        bot.sent.clear()
        await dp.feed_update(bot, make_update(trigger))
        assert intercepted == [], f"competitor leaked cancel for {trigger!r}"
        assert any("bekor qilindi" in (t or "").lower() for t, _ in bot.sent), bot.sent
        assert await storage.get_state(key_for(bot)) is None

    # Admin cancel returns the admin panel keyboard (no competitor leak).
    bot.sent.clear()
    await dp.feed_update(bot, make_update(CANCEL_BTN))
    _, reply_markup = bot.sent[-1]
    admin_names = {b.text for row in admin_main_keyboard().keyboard for b in row}
    kb_names = {b.text for row in reply_markup.keyboard for b in row}
    assert admin_names == kb_names, kb_names
    print("[ OK ] cancel clears active state & returns admin panel")

    # Regression: with NO cancel router the competitor swallows the cancel press.
    s2 = MemoryStorage()
    b2 = ProbeBot()
    leaked: list[str] = []
    dp2 = Dispatcher(storage=s2)
    dp2.include_router(make_competitor(leaked))  # NO cancel router
    await set_state(b2, s2, BroadcastStates.waiting_text)
    await dp2.feed_update(b2, make_update(CANCEL_BTN))
    assert leaked == ["leaked"], leaked
    print("[ OK ] regression: without cancel router the competitor fires (bad)")
    print("\nALL CANCEL ROUTING TESTS PASSED")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
