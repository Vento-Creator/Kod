"""Smoke test for the database + services layers (no network required).

Run with::

    python tests/smoke_test.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile

# Make the project root importable when running this file directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["BOT_TOKEN"] = "1111111110:TEST-TOKEN"
os.environ["ADMIN_IDS"] = "111111,222222"

from config import get_settings  # noqa: E402
from database import Database  # noqa: E402
from database.models import Movie, User  # noqa: E402
from services.movies import (  # noqa: E402
    CodeAlreadyTakenError,
    CodeValidationError,
    MovieService,
)
from services.users import PenaltyKind, apply_flood_penalty  # noqa: E402


async def create_db() -> Database:
    path = os.path.join(os.path.dirname(__file__), "_smoke.db")
    if os.path.exists(path):
        os.remove(path)
    db = Database(path)
    await db.connect()
    return db


async def smoke_run() -> None:
    settings = get_settings()
    assert settings.bot_token == "1111111110:TEST-TOKEN"
    assert settings.admins == [111111, 222222]
    print("[ OK ] settings parse")

    db = await create_db()
    try:
        # --- users -------------------------------------------------
        user = await db.get_or_create_user(1, username="alice", full_name="Alice")
        assert isinstance(user, User) and user.telegram_id == 1
        again = await db.get_or_create_user(1, username="alice", full_name="Alice2")
        assert again.full_name == "Alice2", "username refresh failed"
        assert await db.count_users() == 1

        # --- movies (CRUD + collision) -----------------------------
        service = MovieService(db)
        movie = await service.create("007", "FILE123", "video", "Test movie")
        assert movie.code == "7", "leading-zero normalisation failed"
        assert movie.file_id == "FILE123"
        assert movie.caption == "Test movie"

        # duplicate code must raise
        try:
            await service.create("7", "FILE999", "video", None)
            raise AssertionError("duplicate code did not raise")
        except CodeAlreadyTakenError:
            pass

        # invalid code must raise
        try:
            await service.create("abc", "X", "video", None)
            raise AssertionError("invalid code did not raise")
        except CodeValidationError:
            pass

        # search flow: found + not found + deleted excluded
        found = await service.find("007")
        assert found is not None and found.code == "7"
        assert await service.find("42") is None

        # change code with collision + success
        other = await service.create("1", "FILE111", "video", "Occupied")
        assert other.code == "1"
        try:
            await service.change_code(movie.id, "1")
            raise AssertionError("code change collision did not raise")
        except CodeAlreadyTakenError:
            pass
        changed = await service.change_code(movie.id, "00099")
        assert changed.code == "99"

        # logs
        await db.add_log(user.id, "99")
        await db.add_log(user.id, "404")
        logs = await db.get_recent_logs(user.id, limit=10)
        assert [l.searched_code for l in logs] == ["99", "404"], logs

        # stats
        stats = await db.stats()
        assert stats["users"] == 1 and stats["movies"] == 2, stats
        print("[ OK ] user/movie/log/stats CRUD")

        # --- soft & hard delete ------------------------------------
        await service.soft_delete(movie.id)
        assert await service.find("99") is None, "deleted movie is visible"
        assert await service.find("99", include_deleted=True) is not None
        await service.restore(movie.id)
        assert await service.find("99") is not None
        await service.hard_delete(movie.id)
        assert await db.get_movie_by_id(movie.id) is None
        print("[ OK ] soft/hard delete & restore")

        # --- escalation ladder --------------------------------------
        p1 = await apply_flood_penalty(db, 1)
        p2 = await apply_flood_penalty(db, 1)
        p3 = await apply_flood_penalty(db, 1)
        p4 = await apply_flood_penalty(db, 1)
        p5 = await apply_flood_penalty(db, 1)

        assert p1.kind is PenaltyKind.WARNING
        assert p2.kind is PenaltyKind.TEMP_BAN and p2.ban_minutes == 30
        assert p3.kind is PenaltyKind.TEMP_BAN and p3.ban_minutes == 60
        assert p4.kind is PenaltyKind.TEMP_BAN and p4.ban_minutes == 120
        assert p5.kind is PenaltyKind.PERMANENT_BAN
        print("[ OK ] flood escalation ladder (warn -> 30m -> 1h -> 2h -> perm)")

        # --- ban reflection in db -----------------------------------------
        blocked = await db.get_user(1)
        assert blocked is not None and blocked.is_blocked is True
        assert blocked.warning_count == 5
        print("[ OK ] permanent ban persisted in DB")

        # --- active users (banned users excluded) ---------------------------
        active = await db.get_active_users()
        assert active == [], "banned user should not be active"
        print("[ OK ] get_active_users excludes banned users")

        # --- channels (force-subscribe CRUD) --------------------------------
        from database.models import Channel

        ch = await db.add_channel("-1001234567890", "https://t.me/+abc", "Kino News")
        assert isinstance(ch, Channel) and ch.channel_id == "-1001234567890"
        assert await db.count_channels() == 1
        assert await db.get_channel("-1001234567890") is not None

        ch2 = await db.add_channel("-100999", "https://t.me/+def", "Films UZ")
        listed = await db.list_channels()
        assert [c.channel_id for c in listed] == ["-1001234567890", "-100999"]
        assert await db.count_channels() == 2

        await db.delete_channel("-100999")
        assert await db.get_channel("-100999") is None
        assert await db.count_channels() == 1
        print("[ OK ] channels CRUD (add/list/delete)")
    finally:
        await db.close()
        p = os.path.join(os.path.dirname(__file__), "_smoke.db")
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(p + suffix)
            except FileNotFoundError:
                pass


def main() -> None:
    asyncio.run(smoke_run())
    print("\nALL SMOKE TESTS PASSED ✔")


if __name__ == "__main__":
    main()