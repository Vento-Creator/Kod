"""Movie business logic.

Thin service layer on top of :class:`database.database.Database` that
implements the rules around movie codes (validation + uniqueness) so
handlers never talk to SQL directly.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import settings
from database import Database
from database.models import Movie


class CodeValidationError(ValueError):
    """Raised when a code does not pass format validation."""


class CodeAlreadyTakenError(ValueError):
    """Raised when the code already belongs to another movie."""


@dataclass(slots=True)
class MovieService:
    """Facade around movie CRUD with business-rule enforcement."""

    db: Database

    @staticmethod
    def normalize_code(raw: str) -> str:
        """Strip whitespace, validate the numeric-only length rule and
        normalise leading zeros (``"007"`` == ``"7"``)."""
        code = raw.strip()
        if not code or not code.isdigit() or len(code) > settings.code_max_length:
            raise CodeValidationError(
                "The code must consist of digits only and have at most "
                f"{settings.code_max_length} characters."
            )
        return str(int(code))

    async def create(
        self, code: str, file_id: str, file_type: str, caption: str | None
    ) -> Movie:
        code = self.normalize_code(code)
        if await self.db.code_exists(code):
            raise CodeAlreadyTakenError(f"Code '{code}' is already in use.")
        try:
            return await self.db.add_movie(
                code=code,
                file_id=file_id,
                file_type=file_type,
                caption=caption,
            )
        except Exception:  # pragma: no cover - SQLite UNIQUE race safety net
            raise CodeAlreadyTakenError(
                f"Code '{code}' is already in use."
            ) from None

    async def find(self, code: str, include_deleted: bool = False) -> Movie | None:
        """Search a movie by code (leading zeros ignored); soft-deleted rows
        are hidden unless ``include_deleted`` is set."""
        try:
            normalized = self.normalize_code(code)
        except CodeValidationError:
            return None
        return await self.db.get_movie_by_code(
            normalized, include_deleted=include_deleted
        )

    async def change_code(self, movie_id: int, new_code: str) -> Movie:
        """Update a movie code after uniqueness validation."""
        new_code = self.normalize_code(new_code)
        movie = await self.db.get_movie_by_id(movie_id)
        if movie is None:
            raise ValueError("Movie not found.")
        if new_code == movie.code:
            return movie
        if await self.db.code_exists(new_code, exclude_movie_id=movie_id):
            raise CodeAlreadyTakenError(f"Code '{new_code}' is already in use.")
        await self.db.update_movie(movie_id=movie_id, code=new_code)
        updated = await self.db.get_movie_by_id(movie_id)
        assert updated is not None
        return updated

    async def change_caption(self, movie_id: int, caption: str | None) -> None:
        await self.db.update_movie(movie_id=movie_id, caption=caption)

    async def soft_delete(self, movie_id: int) -> None:
        await self.db.soft_delete_movie(movie_id)

    async def restore(self, movie_id: int) -> None:
        await self.db.restore_movie(movie_id)

    async def hard_delete(self, movie_id: int) -> None:
        await self.db.hard_delete_movie(movie_id)