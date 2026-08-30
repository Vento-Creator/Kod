"""Handlers package - every entry point of the bot."""
from __future__ import annotations

from .cancel import router as cancel_router
from .admin import router as admin_router
from .admin_users import router as admin_users_router
from .common import router as common_router
from .errors import router as errors_router
from .user import router as user_router

__all__ = [
    "cancel_router",
    "admin_router",
    "admin_users_router",
    "common_router",
    "errors_router",
    "user_router",
]