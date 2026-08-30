"""Regression tests for the force-subscribe (majburiy obuna) 3-state check.

Checks that a Telegram API error about the *bot's access* to the channel
(e.g. bot not admin, wrong id) is reported as ``None`` (unverifiable) and is
never mistaken for "user is not subscribed" (``False``).

Run with::

    python tests/test_subscription.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from types import SimpleNamespace

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["BOT_TOKEN"] = "1111111110:TEST-TOKEN"
os.environ["ADMIN_IDS"] = "111111,222222"

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError  # noqa: E402
from database import Database  # noqa: E402
from services.subscription import (  # noqa: E402
    check_channel_subscription,
    get_subscription_status,
)


def fake_member(status: str) -> SimpleNamespace:
    return SimpleNamespace(status=status)


class FakeBot:
    """One-channel scenario controller: how get_chat_member behaves."""

    def __init__(self, behaviour: str) -> None:
        # behaviour: "member" | "left" | "bot_no_access" | "wrong_id"
        self.behaviour = behaviour

    async def get_chat_member(self, chat_id, user_id):
        if self.behaviour == "member":
            return fake_member("member")
        if self.behaviour == "left":
            return fake_member("left")
        if self.behaviour == "bot_no_access":
            raise TelegramForbiddenError(method="getChatMember", message="403 Forbidden: bot was kicked from the chat")
        if self.behaviour == "wrong_id":
            raise TelegramBadRequest(method="getChatMember", message="Bad Request: chat not found")
        raise AssertionError(f"unknown behaviour {self.behaviour!r}")


async def _make_db() -> Database:
    path = os.path.join(os.path.dirname(__file__), "_sub.db")
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(path + suffix)
        except FileNotFoundError:
            pass
    db = Database(path)
    await db.connect()
    await db.add_channel("-1001111111111", "https://t.me/+aaa", "Kino A")
    await db.add_channel("-1002222222222", "https://t.me/+bbb", "Kino B")
    return db


async def run() -> None:
    db = await _make_db()
    try:
        # 1) Subscribed member -> True, no missing/unverifiable channels.
        bot = FakeBot("member")
        assert await check_channel_subscription(bot, "-1001111111111", 7) is True
        missing, unverifiable = await get_subscription_status(bot, db, 7)
        assert missing == [] and unverifiable == [], (missing, unverifiable)
        print("[ OK ] member -> subscribed")

        # 2) 'left' status -> False (verified as NOT subscribed).
        bot = FakeBot("left")
        assert await check_channel_subscription(bot, "-1001111111111", 7) is False
        missing, unverifiable = await get_subscription_status(bot, db, 7)
        assert len(missing) == 2 and unverifiable == []
        print("[ OK ] left -> not subscribed (missing=2)")

        # 3) Bot kicked (403) -> None, must NOT appear as "missing".
        bot = FakeBot("bot_no_access")
        assert await check_channel_subscription(bot, "-1001111111111", 7) is None
        missing, unverifiable = await get_subscription_status(bot, db, 7)
        assert missing == [] and len(unverifiable) == 2
        print("[ OK ] bot kicked -> unverifiable, NOT falsely missing")

        # 4) Wrong chat id -> None (unverifiable), the original bug.
        bot = FakeBot("wrong_id")
        assert await check_channel_subscription(bot, "-1001111111111", 7) is None
        missing, unverifiable = await get_subscription_status(bot, db, 7)
        assert missing == [] and len(unverifiable) == 2, (missing, unverifiable)
        print("[ OK ] chat not found -> unverifiable (regression fixed)")

        print("\nALL SUBSCRIPTION TESTS PASSED ✔")
    finally:
        await db.close()
        path = os.path.join(os.path.dirname(__file__), "_sub.db")
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(path + suffix)
            except FileNotFoundError:
                pass


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()