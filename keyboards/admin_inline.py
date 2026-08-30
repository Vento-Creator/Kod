"""Inline keyboards used across the admin panel and user flows (O'zbek)."""
from __future__ import annotations

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
from database.models import Channel, User

# ---------------------------------------------------------------------- #
# Callback payloads (kept as simple colon-separated strings)
# ---------------------------------------------------------------------- #
CD = {
    "use_suggested_caption": "use_suggested_caption",
    "custom_caption": "custom_caption",
    "no_caption": "no_caption",
    "movie_edit_caption": "movie_edit_caption",
    "movie_edit_code": "movie_edit_code",
    "movie_replace_media": "movie_replace_media",
    "movie_view": "movie_view",
    "movie_toggle": "movie_toggle",
    "movie_hard": "movie_hard",
    "movie_confirm_hard": "movie_confirm_hard",
    "movie_cancel_hard": "movie_cancel_hard",
    "movie_list": "movie_list",
    "movie_page": "movie_page",
    "user_block": "user_block",
    "user_unblock": "user_unblock",
    "user_activity": "user_activity",
    "user_find": "user_find",
    "users_page": "users_page",
    "to_admin": "admin_panel",
    "home": "home",
    "channel_add": "channel_add",
    "channel_list": "channel_list",
    "channel_delete": "channel_delete",
    "sub_check": "sub_check",
}

BACK_BTN = InlineKeyboardButton(text="⬅️ Orqaga", callback_data=CD["to_admin"])
HOME_IN_BTN = InlineKeyboardButton(text="🏠 Bosh menyu", callback_data=CD["home"])


def _back_home() -> list[InlineKeyboardButton]:
    return [BACK_BTN, HOME_IN_BTN]


def caption_choice_keyboard() -> InlineKeyboardMarkup:
    """Buttons shown after the admin uploads a file (caption handling)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 birikkan captionni ishlatish", callback_data=CD["use_suggested_caption"])],
            [InlineKeyboardButton(text="✍️ O'z captionni yozish", callback_data=CD["custom_caption"])],
            [InlineKeyboardButton(text="🚫 Captionsiz", callback_data=CD["no_caption"])],
            _back_home(),
        ]
    )


def movie_controls_keyboard(movie_id: int, is_deleted: bool) -> InlineKeyboardMarkup:
    """Actions available for a single movie card."""
    toggle_text = "♻️ Qayta tiklash" if is_deleted else "🗑️ O'chirish"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Sarlavha", callback_data=f"{CD['movie_edit_caption']}:{movie_id}"),
             InlineKeyboardButton(text="🔢 Kod", callback_data=f"{CD['movie_edit_code']}:{movie_id}")],
            [InlineKeyboardButton(text="🖼️ Media almashtirish", callback_data=f"{CD['movie_replace_media']}:{movie_id}"),
             InlineKeyboardButton(text="📤 Menga yuborish", callback_data=f"{CD['movie_view']}:{movie_id}")],
            [InlineKeyboardButton(text=toggle_text, callback_data=f"{CD['movie_toggle']}:{movie_id}"),
             InlineKeyboardButton(text="💣 Butunlay o'chirish", callback_data=f"{CD['movie_hard']}:{movie_id}")],
            _back_home(),
        ]
    )


def confirm_hard_delete_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    """Two-step confirmation before permanently removing a movie."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Ha, butunlay o'chir", callback_data=f"{CD['movie_confirm_hard']}:{movie_id}"),
             InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{CD['movie_cancel_hard']}:{movie_id}")],
        ]
    )


def to_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Back to admin panel + home row."""
    return InlineKeyboardMarkup(inline_keyboard=[_back_home()])


def users_pagination_keyboard(
    users: list[User], total_pages: int, page: int,
) -> InlineKeyboardMarkup:
    """List page with per-user actions (block/unblock, activity, search)."""
    rows: list[list[InlineKeyboardButton]] = []

    for user in users:
        badge = "🚫" if user.is_blocked else "✅"
        rows.append(
            [InlineKeyboardButton(text=f"{badge} {user.display_name}", callback_data=f"{CD['user_activity']}:{user.telegram_id}")]
        )
        action_buttons: list[InlineKeyboardButton] = []
        if user.is_blocked:
            action_buttons.append(
                InlineKeyboardButton(text="🔓 Blokdan chiqarish", callback_data=f"{CD['user_unblock']}:{user.telegram_id}")
            )
        else:
            action_buttons.append(
                InlineKeyboardButton(text="🔒 Bloklash", callback_data=f"{CD['user_block']}:{user.telegram_id}")
            )
        action_buttons.append(
            InlineKeyboardButton(text="🗂 Faoliyat", callback_data=f"{CD['user_activity']}:{user.telegram_id}")
        )
        rows.append(action_buttons)

    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"{CD['users_page']}:{page - 1}"))
    total_label = max(1, total_pages)
    nav.append(InlineKeyboardButton(text=f"{page} / {total_label}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"{CD['users_page']}:{page + 1}"))
    rows.append(nav)

    rows.append([InlineKeyboardButton(text="🔍 Foydalanuvchini qidirish (id / @username)", callback_data=CD["user_find"])])
    rows.append(_back_home())

    return InlineKeyboardMarkup(inline_keyboard=rows)


def search_results_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard attached to a user-found movie (search again + home)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Boshqa kino qidirish", callback_data="search_new")],
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="home")],
        ]
    )


def admin_search_start_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown when admin enters the 'search by code' prompt."""
    return InlineKeyboardMarkup(inline_keyboard=[_back_home()])


# ---------------------------------------------------------------------- #
# Force-subscribe (channels) admin keys
# ---------------------------------------------------------------------- #
def channels_menu_keyboard() -> InlineKeyboardMarkup:
    """Admin entry menu for the '📢 Kanallarni boshqarish' section."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data=CD["channel_add"])],
            [InlineKeyboardButton(text="📋 Kanallar ro'yxati", callback_data=CD["channel_list"])],
            _back_home(),
        ]
    )


def channels_list_keyboard(channels: list[Channel]) -> InlineKeyboardMarkup:
    """Active required channels with a delete button under each one."""
    rows: list[list[InlineKeyboardButton]] = []
    for channel in channels:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"❌ {channel.channel_name}",
                    callback_data=f"{CD['channel_delete']}:{channel.channel_id}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data=CD["channel_add"])]
    )
    rows.append(_back_home())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscription_required_keyboard(missing: list[Channel]) -> InlineKeyboardMarkup:
    """Prompt for a not-subscribed user.

    One join button (``url``) per missing channel plus a
    "✅ Tekshirish" button that re-verifies subscription.
    """
    rows: list[list[InlineKeyboardButton]] = []
    for channel in missing:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"📢 {channel.channel_name}", url=channel.channel_url
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="✅ Tekshirish", callback_data=CD["sub_check"])]
    )
    # Escape hatch: never trap the user in the subscription screen.
    rows.append(
        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data=CD["home"])]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline cancel button for callback edits."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_inline")]
        ]
    )


def movies_list_keyboard(movies: list, page: int = 1, per_page: int = 10) -> InlineKeyboardMarkup:
    """Paginated list of movies for admin catalog."""
    rows: list[list[InlineKeyboardButton]] = []
    
    for movie in movies:
        caption = getattr(movie, 'caption', None) or "No caption"
        code = getattr(movie, 'code', '???')
        movie_id = getattr(movie, 'id', 0)
        caption_preview = caption[:30] + "..." if caption and len(caption) > 30 else caption
        rows.append(
            [InlineKeyboardButton(
                text=f"📎 {code} - {caption_preview}",
                callback_data=f"{CD['movie_view']}:{movie_id}"
            )]
        )
    
    # Pagination controls
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"{CD['movie_page']}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page}", callback_data="noop"))
    nav.append(InlineKeyboardButton(text="➡️", callback_data=f"{CD['movie_page']}:{page + 1}"))
    rows.append(nav)
    
    rows.append(_back_home())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def movies_catalog_menu_keyboard() -> InlineKeyboardMarkup:
    """Admin entry menu for the '📚 Barcha kinolar' section."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Kinolar ro'yxati", callback_data=CD["movie_list"])],
            _back_home(),
        ]
    )