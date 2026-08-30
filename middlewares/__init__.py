"""Middleware package.

* :class:`~.db.DatabaseMiddleware` injects the shared database into every
  handler through the ``data`` dict.
* :class:`~.throttling.AntiFloodMiddleware` implements the escalating
  anti-spam / temp-ban protection.
"""
from __future__ import annotations

from .db import DatabaseMiddleware
from .throttling import AntiFloodMiddleware

__all__ = ["AntiFloodMiddleware", "DatabaseMiddleware"]