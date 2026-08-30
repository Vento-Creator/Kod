"""User helpers: registration and the escalating flood-breach ladder.

Escalation rules:

+----------+--------------------------------------------+
| Breach # | Punishment                                   |
+==========+==============================================+
| 1        | warning message                               |
| 2        | 30  minutes temporary ban                     |
| 3        | 60  minutes temporary ban                     |
| 4        | 120 minutes temporary ban                     |
| 5 and +  | permanent automatic ban (is_blocked=1)        |
+----------+--------------------------------------------+

Texts are localized in utils.texts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from config import settings
from database import Database, utcnow
from database.models import User
from utils import texts


class PenaltyKind(str, Enum):
    """The three kinds of punishment produced by the escalation ladder."""

    WARNING = "warning"
    TEMP_BAN = "temp_ban"
    PERMANENT_BAN = "permanent_ban"


@dataclass(frozen=True, slots=True)
class FloodPenalty:
    """Immutable description of the punishment applied for a breach."""

    level: int
    kind: PenaltyKind
    ban_minutes: int | None = None
    ban_until: datetime | None = None

    @property
    def user_message(self) -> str:
        """Public text that is sent to the punished user once (in O'zbek)."""
        if self.kind is PenaltyKind.WARNING:
            return texts.FLOOD_WARNING
        if self.kind is PenaltyKind.PERMANENT_BAN:
            return texts.FLOOD_PERMANENT
        return texts.FLOOD_TEMP_BAN.format(
            level=self.level,
            minutes=self.ban_minutes,
            time_left=texts.fmt_time_remaining(self.ban_until),
        )


def _build_penalty(level: int) -> FloodPenalty:
    """Map a breach number to its penalty according to the escalation table."""
    if level >= settings.permanent_ban_level:
        return FloodPenalty(level=level, kind=PenaltyKind.PERMANENT_BAN)

    ban_minutes = settings.ban_duration_by_level.get(level)
    if ban_minutes is not None:
        ban_until = utcnow() + timedelta(minutes=ban_minutes)
        return FloodPenalty(
            level=level,
            kind=PenaltyKind.TEMP_BAN,
            ban_minutes=ban_minutes,
            ban_until=ban_until,
        )

    return FloodPenalty(level=level, kind=PenaltyKind.WARNING)


async def register_user(
    db: Database,
    telegram_id: int,
    username: str | None = None,
    full_name: str | None = None,
) -> User:
    """Idempotently register/refresh the user row."""
    return await db.get_or_create_user(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
    )


async def apply_flood_penalty(db: Database, telegram_id: int) -> FloodPenalty:
    """Persist the next escalation step for a flooding user.

    The current breach level is read from ``users.warning_count`` so the
    ladder survives bot restarts.
    """
    user = await db.get_or_create_user(telegram_id=telegram_id)
    next_level = user.warning_count + 1
    penalty = _build_penalty(next_level)

    if penalty.kind is PenaltyKind.WARNING:
        await db.conn.execute(
            "UPDATE users SET warning_count = ? WHERE telegram_id = ?",
            (next_level, telegram_id),
        )
        await db.conn.commit()
    elif penalty.kind is PenaltyKind.TEMP_BAN:
        assert penalty.ban_until is not None
        await db.set_user_temp_ban(
            telegram_id=telegram_id,
            ban_until=penalty.ban_until,
            warning_count=next_level,
        )
    else:  # permanent ban
        await db.ban_user_permanently(
            telegram_id=telegram_id, warning_count=next_level
        )

    return penalty