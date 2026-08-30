"""Behavioral test for the anti-flood middleware (no network needed).

Run with::

    python tests/test_antiflood.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["BOT_TOKEN"] = "1111111110:TEST-TOKEN"
os.environ["ADMIN_IDS"] = "111111,222222"

import database.database as db_mod  # noqa: E402
import middlewares.throttling as throttling_mod  # noqa: E402
import services.users as users_mod  # noqa: E402
from aiogram.types import Chat, Message, User as TgUser  # noqa: E402
from database import Database  # noqa: E402
from middlewares import AntiFloodMiddleware  # noqa: E402


class FakeClock:
    """Controllable clock shared with every module under test."""

    def __init__(self, start: datetime) -> None:
        self.now = start

    def advance(self, delta) -> None:
        if isinstance(delta, timedelta):
            self.now += delta
        else:
            self.now += timedelta(seconds=delta)


def make_message(user_id: int, chat_id: int, text: str, bot: object) -> Message:
    chat = Chat(id=chat_id, type="private")
    user = TgUser(id=user_id, is_bot=False, first_name="Tester")
    msg = Message(message_id=1, date=datetime.now(timezone.utc), chat=chat,
                  from_user=user, text=text)
    object.__setattr__(msg, "_bot", bot)
    return msg


async def run() -> None:
    path = os.path.join(os.path.dirname(__file__), "_flood.db")
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(path + suffix)
        except FileNotFoundError:
            pass

    db = Database(path)
    await db.connect()

    clock = FakeClock(datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
    db_mod.utcnow = lambda: clock.now
    throttling_mod.utcnow = lambda: clock.now
    users_mod.utcnow = lambda: clock.now  # services.users imported utcnow by value

    sent_notices: list[str] = []

    class FakeBot:
        async def send_message(self, chat_id: int, text: str, **kwargs):
            sent_notices.append(text)
            return SimpleNamespace()

    bot = FakeBot()
    mw = AntiFloodMiddleware(db)
    handled: list[str] = []

    async def handler(event, data):
        handled.append(event.text)
        return None

    def msg() -> Message:
        return make_message(777, 777, "123", bot)

    try:
        # 1) First request passes and reaches the handler.
        await mw(handler, msg(), {})
        assert handled == ["123"], handled

        # 2) Instant second request -> flood breach #1: warning, not handled.
        await mw(handler, msg(), {})  # flood
        await mw(handler, msg(), {})  # part of the same burst
        assert handled == ["123"], "flood messages must not reach the handler"
        assert len(sent_notices) == 1 and "ogohlantirish" in sent_notices[0].lower()
        user = await db.get_user(777)
        assert user is not None and user.warning_count == 1
        print("[ OK ] breach #1 -> warning, burst coalesced")

        # 3) Quiet period, then a new quick burst -> breach #2 = 30 min ban.
        clock.advance(31)
        await mw(handler, msg(), {})  # quiet pass
        clock.advance(0.5)
        await mw(handler, msg(), {})  # flood -> temp ban
        user = await db.get_user(777)
        assert user.warning_count == 2, user.warning_count
        remaining = user.ban_until - clock.now  # type: ignore[union-attr]
        assert timedelta(minutes=29) < remaining <= timedelta(minutes=30), remaining
        print("[ OK ] breach #2 -> 30 min temp ban")

        # 4) While the ban is active all further messages are auto-ignored.
        clock.advance(5)
        await mw(handler, msg(), {})  # auto-ignored
        user = await db.get_user(777)
        assert user.warning_count == 2
        assert len(handled) == 2, "banned messages must be ignored"
        print("[ OK ] auto-ignore during active ban")

        # 5) Ban expiry -> new burst -> breach #3 -> 60 min ban.
        clock.advance(3601)
        await mw(handler, msg(), {})  # quiet pass (ban expired)
        clock.advance(0.5)
        await mw(handler, msg(), {})  # flood -> 60 min
        user = await db.get_user(777)
        assert user.warning_count == 3, user.warning_count
        assert (user.ban_until - clock.now) > timedelta(minutes=59)  # type: ignore[union-attr]
        print("[ OK ] breach #3 -> 60 min temp ban")

        # 6) breach #4 -> 120 min, then breach #5 -> permanent ban.
        clock.advance(3700)
        await mw(handler, msg(), {})  # quiet pass (ban expired)
        clock.advance(0.5)
        await mw(handler, msg(), {})  # flood -> level 4 (120 min ban)
        user = await db.get_user(777)
        assert user.warning_count == 4, user.warning_count
        remaining = user.ban_until - clock.now  # type: ignore[union-attr]
        assert timedelta(minutes=119) < remaining <= timedelta(minutes=120), remaining
        assert not user.is_blocked
        print("[ OK ] breach #4 -> 120 min temp ban")

        # Expire the 120-min ban to reach breach #5.
        clock.advance(timedelta(minutes=121))
        await mw(handler, msg(), {})  # quiet pass
        clock.advance(0.5)
        await mw(handler, msg(), {})  # flood -> permanent ban
        user = await db.get_user(777)
        assert user.warning_count == 5, user.warning_count
        assert user.is_blocked, "permanent ban expected"
        print("[ OK ] breach #5 -> permanent ban")

        # Permanently banned -> every message auto-ignored, count frozen.
        clock.advance(1)
        await mw(handler, msg(), {})  # no escalation while permabanned
        user = await db.get_user(777)
        assert user.warning_count == 5
        assert len(handled) == 5, len(handled)
        print("[ OK ] auto-ignore while permabanned")
        print("\nALL ANTIFLOOD TESTS PASSED")
    finally:
        await db.close()
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(path + suffix)
            except FileNotFoundError:
                pass


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()