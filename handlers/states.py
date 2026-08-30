"""Finite state machine definitions for the admin dialogs."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class UploadStates(StatesGroup):
    """Multi-step flow: media -> caption -> unique numeric code."""

    waiting_file = State()
    waiting_caption = State()
    waiting_code = State()


class EditStates(StatesGroup):
    """Edit-caption, change-code, and media-replace dialogs (movie id kept in state data)."""

    waiting_new_caption = State()
    waiting_new_code = State()
    waiting_for_new_media = State()


class SearchStates(StatesGroup):
    """Waiting for a movie code to display/edit."""

    waiting_code = State()


class UserAdminStates(StatesGroup):
    """User-management dialogs: finding a user id / @username."""

    waiting_identifier = State()


class BroadcastStates(StatesGroup):
    """Waiting for the broadcast text from the admin."""

    waiting_text = State()


class ChannelStates(StatesGroup):
    """Force-subscribe channel management: id -> invite link -> name."""

    waiting_channel_id = State()
    waiting_channel_link = State()
    waiting_channel_name = State()