"""Reply keyboards used by the bot (O'zbek labels)."""
from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# ---------------------------------------------------------------------- #
# Button labels
# ---------------------------------------------------------------------- #
HOME_SEARCH_BTN = "🎬 Kino qidirish"
HOME_HELP_BTN = "ℹ️ Yordam"

ADMIN_UPLOAD_BTN = "⬆️ Yuklash"
ADMIN_SEARCH_BTN = "🔍 Kod qidirish"
ADMIN_USERS_BTN = "👥 Foydalanuvchilar"
ADMIN_BROADCAST_BTN = "📣 Yangilik"
ADMIN_STATS_BTN = "📊 Statistika"
ADMIN_CHANNELS_BTN = "📢 Kanallarni boshqarish"
ADMIN_MOVIES_BTN = "📚 Barcha kinolar"
ADMIN_HOME_BTN = "🏠 Bosh menyu"

CANCEL_BTN = "❌ Bekor qilish"


def home_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard shown to regular users."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=HOME_SEARCH_BTN)],
            [KeyboardButton(text=HOME_HELP_BTN)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Kino kodini yuboring...",
    )


def admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard shown to admins - gateway to every admin feature."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADMIN_UPLOAD_BTN), KeyboardButton(text=ADMIN_SEARCH_BTN)],
            [KeyboardButton(text=ADMIN_USERS_BTN), KeyboardButton(text=ADMIN_STATS_BTN)],
            [KeyboardButton(text=ADMIN_CHANNELS_BTN), KeyboardButton(text=ADMIN_MOVIES_BTN)],
            [KeyboardButton(text=ADMIN_BROADCAST_BTN), KeyboardButton(text=ADMIN_HOME_BTN)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Admin paneli...",
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard that lets an admin abort the current FSM flow."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_BTN)]],
        resize_keyboard=True,
    )