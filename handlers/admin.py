"""Admin panel: media upload (CRUD), movie search, editing and deletion.

Only users listed in ``settings.admins`` are allowed - enforced by the
``AdminFilter`` attached to the router. All texts are in O'zbek.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database
from database.models import Channel, Movie
from handlers.admin_filter import AdminFilter
from handlers.states import ChannelStates, EditStates, SearchStates, UploadStates
from keyboards.admin_inline import (
    CD,
    cancel_inline_keyboard,
    caption_choice_keyboard,
    channels_list_keyboard,
    channels_menu_keyboard,
    confirm_hard_delete_keyboard,
    movie_controls_keyboard,
    movies_catalog_menu_keyboard,
    movies_list_keyboard,
    to_admin_panel_keyboard,
)
from keyboards.reply import (
    ADMIN_CHANNELS_BTN,
    ADMIN_MOVIES_BTN,
    ADMIN_SEARCH_BTN,
    ADMIN_STATS_BTN,
    ADMIN_UPLOAD_BTN,
    admin_main_keyboard,
    cancel_keyboard,
)
from services.movies import CodeAlreadyTakenError, CodeValidationError, MovieService
from utils import esc, extract_media, send_media, texts

logger = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


def render_movie_card(movie: Movie) -> str:
    created = (
        movie.created_at.strftime("%Y-%m-%d %H:%M UTC")
        if movie.created_at
        else "noma'lum"
    )
    caption = esc(movie.caption) or "-"
    status = "🚫 yashirilgan" if movie.is_deleted else "✅ ko'rsatiladi"
    return texts.MOVIE_CARD.format(
        code=esc(movie.code),
        file_type=esc(movie.file_type),
        caption=caption,
        status=status,
        created=esc(created),
    )


# ---------------------------------------------------------------------- #
# Panel entry / stats
# ---------------------------------------------------------------------- #
@router.message(Command("admin"))
async def on_admin_command(message: Message) -> None:
    await message.answer(texts.PANEL_TEXT, reply_markup=admin_main_keyboard())


@router.message(F.text == ADMIN_STATS_BTN)
async def on_admin_stats(message: Message, db: Database) -> None:
    stats = await db.stats()
    await message.answer(
        texts.STATS_TEXT.format(
            users=stats["users"],
            movies=stats["movies"],
            active_movies=stats["active_movies"],
            searches=stats["searches"],
        )
    )


# ---------------------------------------------------------------------- #
# Upload flow: file -> caption (with suggestion) -> unique code
# ---------------------------------------------------------------------- #
@router.message(F.text == ADMIN_UPLOAD_BTN)
async def on_upload_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(UploadStates.waiting_file)
    await message.answer(texts.UPLOAD_STEP1, reply_markup=cancel_keyboard())


@router.message(UploadStates.waiting_file)
async def on_upload_file(message: Message, state: FSMContext) -> None:
    media = extract_media(message)
    if media is None:
        await message.answer(texts.UPLOAD_NO_MEDIA)
        return
    file_id, file_type = media
    suggested = message.caption or message.text or ""
    await state.update_data(file_id=file_id, file_type=file_type)
    if suggested:
        await state.update_data(suggested_caption=suggested)
        await message.answer(
            texts.UPLOAD_MEDIA_RECEIVED.format(caption=esc(suggested)),
            reply_markup=caption_choice_keyboard(),
        )
    else:
        await message.answer(texts.UPLOAD_NO_CAPTION_MSG, reply_markup=caption_choice_keyboard())
    await state.set_state(UploadStates.waiting_caption)


@router.callback_query(UploadStates.waiting_caption, F.data == CD["use_suggested_caption"])
async def on_upload_use_suggested(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.update_data(caption=data.get("suggested_caption"))
    await callback.answer("Caption tanlandi ✔️")
    await _prompt_for_code(callback.message, state)


@router.callback_query(UploadStates.waiting_caption, F.data == CD["no_caption"])
async def on_upload_no_caption(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(caption=None)
    await callback.answer("Captionsiz ✔️")
    await _prompt_for_code(callback.message, state)


@router.callback_query(UploadStates.waiting_caption, F.data == CD["custom_caption"])
async def on_upload_custom_caption(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        texts.EDIT_CAPTION_EMPTY_PROMPT, reply_markup=to_admin_panel_keyboard()
    )


@router.message(UploadStates.waiting_caption)
async def on_upload_caption_text(message: Message, state: FSMContext) -> None:
    caption = message.text.strip()
    await state.update_data(caption=caption or None)
    await _prompt_for_code(message, state)


async def _prompt_for_code(msg: Message, state: FSMContext) -> None:
    await state.set_state(UploadStates.waiting_code)
    await msg.answer(texts.UPLOAD_STEP3_CODE, reply_markup=cancel_keyboard())


@router.message(UploadStates.waiting_code)
async def on_upload_code(message: Message, state: FSMContext, db: Database) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer(texts.CODE_INVALID.format(error=texts.DIGITS_ONLY))
        return
    data = await state.get_data()
    try:
        movie = await MovieService(db).create(
            code=message.text.strip(),
            file_id=data["file_id"],
            file_type=data["file_type"],
            caption=data.get("caption"),
        )
    except CodeAlreadyTakenError:
        await message.answer(
            texts.CODE_TAKEN.format(code=esc(message.text.strip())),
            reply_markup=cancel_keyboard(),
        )
        return
    except CodeValidationError as exc:
        await message.answer(
            texts.CODE_INVALID.format(error=esc(str(exc))),
            reply_markup=cancel_keyboard(),
        )
        return
    await state.clear()
    await message.answer(
        "✅ <b>Kino saqlandi</b>\n\n" + render_movie_card(movie),
        reply_markup=movie_controls_keyboard(movie.id, movie.is_deleted),
    )


# ---------------------------------------------------------------------- #
# Search by code -> movie card with controls
# ---------------------------------------------------------------------- #
@router.message(F.text == ADMIN_SEARCH_BTN)
async def on_search_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SearchStates.waiting_code)
    await message.answer(texts.UPLOAD_STEP3_CODE, reply_markup=cancel_keyboard())


@router.message(SearchStates.waiting_code)
async def on_search_code(message: Message, state: FSMContext, db: Database) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer(texts.INVALID_CODE_TEXT)
        return
    code = str(int(message.text.strip()))
    movie = await MovieService(db).find(code, include_deleted=True)
    if movie is None:
        await message.answer(
            texts.NOT_FOUND_TEXT.format(code=esc(code)),
            reply_markup=cancel_keyboard(),
        )
        return
    await state.clear()
    await message.answer(
        render_movie_card(movie),
        reply_markup=movie_controls_keyboard(movie.id, movie.is_deleted),
    )


# ---------------------------------------------------------------------- #
# Movie inline controls
# ---------------------------------------------------------------------- #
@router.callback_query(F.data.startswith("movie_view:"))
async def on_movie_view(callback: CallbackQuery, db: Database) -> None:
    movie_id = int(callback.data.split(":", 1)[1])
    movie = await db.get_movie_by_id(movie_id)
    await callback.answer()
    if movie is None:
        await callback.message.edit_text(texts.NO_SUCH_MOVIE, reply_markup=to_admin_panel_keyboard())
        return
    ok = await send_media(
        callback.bot, callback.message.chat.id, movie,
        reply_markup=to_admin_panel_keyboard(),
    )
    if not ok:
        await callback.message.edit_text(texts.CANNOT_REPLAY_MEDIA, reply_markup=to_admin_panel_keyboard())


@router.callback_query(F.data.startswith("movie_toggle:"))
async def on_movie_toggle(callback: CallbackQuery, db: Database) -> None:
    movie_id = int(callback.data.split(":", 1)[1])
    movie = await db.get_movie_by_id(movie_id)
    if movie is None:
        await callback.answer(texts.NO_SUCH_MOVIE, show_alert=True)
        return
    service = MovieService(db)
    if movie.is_deleted:
        await service.restore(movie_id)
        action = "tiklandi"
    else:
        await service.soft_delete(movie_id)
        action = "yashirildi"
    await callback.answer(f"Kino {action} ✔️")
    updated = await db.get_movie_by_id(movie_id)
    assert updated is not None
    await callback.message.edit_text(
        render_movie_card(updated),
        reply_markup=movie_controls_keyboard(updated.id, updated.is_deleted),
    )


@router.callback_query(F.data.startswith("movie_hard:"))
async def on_movie_hard_delete(callback: CallbackQuery) -> None:
    movie_id = int(callback.data.split(":", 1)[1])
    await callback.answer()
    await callback.message.edit_text(
        texts.HARD_DELETE_PROMPT, reply_markup=confirm_hard_delete_keyboard(movie_id)
    )


@router.callback_query(F.data.startswith("movie_confirm_hard:"))
async def on_movie_confirm_hard(callback: CallbackQuery, db: Database) -> None:
    movie_id = int(callback.data.split(":", 1)[1])
    await MovieService(db).hard_delete(movie_id)
    await callback.answer("Kino butunlay o'chirildi ✔️")
    if callback.message is not None:
        await callback.message.edit_text(
            texts.PERMANENTLY_DELETED, reply_markup=to_admin_panel_keyboard()
        )


@router.callback_query(F.data.startswith("movie_cancel_hard:"))
async def on_movie_cancel_hard(callback: CallbackQuery, db: Database) -> None:
    movie_id = int(callback.data.split(":", 1)[1])
    movie = await db.get_movie_by_id(movie_id)
    await callback.answer("Bekor qilindi ✔️")
    if movie is None:
        return
    await callback.message.edit_text(
        render_movie_card(movie),
        reply_markup=movie_controls_keyboard(movie.id, movie.is_deleted),
    )


@router.callback_query(F.data.startswith("movie_edit_caption:"))
async def on_edit_caption_start(callback: CallbackQuery, state: FSMContext) -> None:
    movie_id = int(callback.data.split(":", 1)[1])
    await state.set_state(EditStates.waiting_new_caption)
    await state.update_data(movie_id=movie_id)
    await callback.answer()
    await callback.message.edit_text(
        texts.EDIT_CAPTION_PROMPT, reply_markup=cancel_inline_keyboard()
    )
    # EditStates is an inline-controlled prompt with no reply Cancel button,
    # so present the Cancel reply-keyboard so the global cancel handler can
    # intercept the "❌ Bekor qilish" press from this state too.
    await callback.message.answer(texts.CANCEL_HELP, reply_markup=cancel_keyboard())


@router.message(EditStates.waiting_new_caption)
async def on_edit_caption_text(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    movie_id: int = data["movie_id"]
    await MovieService(db).change_caption(movie_id, caption=message.text or None)
    await state.clear()
    movie = await db.get_movie_by_id(movie_id)
    if movie is None:
        await message.answer(texts.NO_SUCH_MOVIE)
        return
    await message.answer(
        "✅ <b>Caption yangilandi</b>\n\n" + render_movie_card(movie),
        reply_markup=movie_controls_keyboard(movie.id, movie.is_deleted),
    )


@router.callback_query(F.data.startswith("movie_edit_code:"))
async def on_edit_code_start(callback: CallbackQuery, state: FSMContext) -> None:
    movie_id = int(callback.data.split(":", 1)[1])
    await state.set_state(EditStates.waiting_new_code)
    await state.update_data(movie_id=movie_id)
    await callback.answer()
    await callback.message.edit_text(
        texts.EDIT_CODE_PROMPT, reply_markup=cancel_inline_keyboard()
    )
    # Expose the global Cancel button for this inline-started text-input state
    # (see on_edit_caption_start).
    await callback.message.answer(texts.CANCEL_HELP, reply_markup=cancel_keyboard())


@router.message(EditStates.waiting_new_code)
async def on_edit_code(message: Message, state: FSMContext, db: Database) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer(texts.INVALID_CODE_TEXT)
        return
    data = await state.get_data()
    movie_id: int = data["movie_id"]
    try:
        movie = await MovieService(db).change_code(movie_id, new_code=message.text)
    except CodeAlreadyTakenError:
        await message.answer(
            texts.CODE_TAKEN.format(code=esc(message.text.strip())),
            reply_markup=cancel_keyboard(),
        )
        return
    except CodeValidationError as exc:
        await message.answer(
            texts.CODE_INVALID.format(error=esc(str(exc))),
            reply_markup=cancel_keyboard(),
        )
        return
    await state.clear()
    await message.answer(
        "✅ <b>Kod yangilandi</b>\n\n" + render_movie_card(movie),
        reply_markup=movie_controls_keyboard(movie.id, movie.is_deleted),
    )


@router.callback_query(F.data.startswith("movie_replace_media:"))
async def on_replace_media_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Start media replacement flow for a movie."""
    movie_id = int(callback.data.split(":", 1)[1])
    await state.set_state(EditStates.waiting_for_new_media)
    await state.update_data(movie_id=movie_id)
    await callback.answer()
    await callback.message.edit_text(
        texts.MEDIA_REPLACE_PROMPT, reply_markup=cancel_inline_keyboard()
    )


@router.message(EditStates.waiting_for_new_media)
async def on_replace_media(message: Message, state: FSMContext, db: Database) -> None:
    """Handle new media file for replacement."""
    media = extract_media(message)
    if media is None:
        await message.answer(texts.NO_MEDIA_ERROR, reply_markup=cancel_keyboard())
        return
    
    file_id, file_type = media
    data = await state.get_data()
    movie_id: int = data["movie_id"]
    
    movie = await db.get_movie_by_id(movie_id)
    if movie is None:
        await state.clear()
        await message.answer(texts.NO_SUCH_MOVIE, reply_markup=admin_main_keyboard())
        return
    
    # Update the movie with new media
    await db.update_movie_media(movie_id, file_id, file_type)
    await state.clear()
    
    updated_movie = await db.get_movie_by_id(movie_id)
    assert updated_movie is not None
    
    await message.answer(
        "✅ <b>Media almashtirildi</b>\n\n" + render_movie_card(updated_movie),
        reply_markup=movie_controls_keyboard(updated_movie.id, updated_movie.is_deleted),
    )


# ---------------------------------------------------------------------- #
# Force-subscribe (kanallarni boshqarish)
# ---------------------------------------------------------------------- #
def _render_channels(channels: list[Channel]) -> str:
    """Human readable channel list used in the admin channel screen."""
    if not channels:
        return texts.CHANNELS_EMPTY
    lines = "\n\n".join(
        f"📢 <b>{esc(channel.channel_name)}</b>\n"
        f"🆔 <code>{esc(channel.channel_id)}</code>\n"
        f"🔗 {esc(channel.channel_url)}"
        for channel in channels
    )
    return texts.CHANNELS_LIST.format(lines=lines)


@router.message(F.text == ADMIN_CHANNELS_BTN)
async def on_channels_start(message: Message, state: FSMContext) -> None:
    """Open the '📢 Kanallarni boshqarish' admin section."""
    await state.clear()
    await message.answer(texts.CHANNELS_MENU, reply_markup=channels_menu_keyboard())


@router.message(F.text == ADMIN_MOVIES_BTN)
async def on_movies_catalog_start(message: Message, state: FSMContext) -> None:
    """Open the '📚 Barcha kinolar' admin section."""
    await state.clear()
    await message.answer(texts.MOVIES_CATALOG_MENU, reply_markup=movies_catalog_menu_keyboard())


@router.callback_query(F.data == CD["movie_list"])
async def on_movie_list(callback: CallbackQuery, db: Database) -> None:
    """Show paginated list of all movies."""
    await callback.answer()
    if callback.message is None:
        return
    movies = await db.list_movies(offset=0, limit=10, include_deleted=True)
    if not movies:
        await callback.message.edit_text(texts.MOVIES_EMPTY, reply_markup=movies_catalog_menu_keyboard())
        return
    await callback.message.edit_text(
        f"📚 <b>Barcha kinolar</b>\n\nJami: {len(movies)} ta",
        reply_markup=movies_list_keyboard(movies, page=1)
    )


@router.callback_query(F.data.startswith(f"{CD['movie_page']}:"))
async def on_movie_page(callback: CallbackQuery, db: Database) -> None:
    """Handle movie list pagination."""
    page = int(callback.data.split(":", 1)[1])
    await callback.answer()
    if callback.message is None:
        return
    offset = (page - 1) * 10
    movies = await db.list_movies(offset=offset, limit=10, include_deleted=True)
    if not movies:
        await callback.message.edit_text(texts.MOVIES_EMPTY, reply_markup=movies_catalog_menu_keyboard())
        return
    await callback.message.edit_text(
        f"📚 <b>Barcha kinolar</b>\n\nJami: {len(movies)} ta",
        reply_markup=movies_list_keyboard(movies, page=page)
    )


@router.callback_query(F.data == CD["channel_add"])
async def on_channel_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 1/3 of the add-channel flow: ask for the channel id."""
    await state.set_state(ChannelStates.waiting_channel_id)
    await state.update_data(channel_id=None, channel_url=None, channel_name=None)
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(
            texts.CHANNEL_ADD_STEP_ID, reply_markup=cancel_inline_keyboard()
        )
        # Also send a message with the reply keyboard for user input
        await callback.message.answer(texts.CHANNEL_ADD_STEP_ID, reply_markup=cancel_keyboard())


@router.message(ChannelStates.waiting_channel_id)
async def on_channel_id(
    message: Message, state: FSMContext, db: Database
) -> None:
    raw = (message.text or "").strip()
    
    # Handle @username input - fetch channel ID from Telegram
    if raw.startswith("@"):
        try:
            chat = await message.bot.get_chat(raw)
            channel_id = str(chat.id)
        except Exception:
            await message.answer(texts.CHANNEL_ADD_INVALID_ID)
            return
    else:
        # Handle numeric input - auto-prepend -100 if needed
        digits = raw[1:] if raw.startswith("-") else raw
        if not raw or not digits.isdigit():
            await message.answer(texts.CHANNEL_ADD_INVALID_ID)
            return
        
        # Auto-prepend -100 if user typed positive numbers
        if raw.isdigit():
            channel_id = f"-100{raw}"
        else:
            channel_id = raw
    
    if await db.get_channel(channel_id) is not None:
        await message.answer(texts.CHANNEL_DUPLICATE_ID)
        return
    await state.update_data(channel_id=channel_id)
    await state.set_state(ChannelStates.waiting_channel_link)
    await message.answer(texts.CHANNEL_ADD_STEP_LINK, reply_markup=cancel_keyboard())


@router.message(ChannelStates.waiting_channel_link)
async def on_channel_link(
    message: Message, state: FSMContext
) -> None:
    link = (message.text or "").strip()
    if not link.startswith("https://t.me/"):
        await message.answer(texts.CHANNEL_ADD_INVALID_LINK)
        return
    await state.update_data(channel_url=link)
    await state.set_state(ChannelStates.waiting_channel_name)
    await message.answer(texts.CHANNEL_ADD_STEP_NAME, reply_markup=cancel_keyboard())


@router.message(ChannelStates.waiting_channel_name)
async def on_channel_name(
    message: Message, state: FSMContext, db: Database
) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer(texts.CHANNEL_ADD_INVALID_NAME)
        return
    data = await state.get_data()
    channel = await db.add_channel(
        channel_id=data["channel_id"],
        channel_url=data["channel_url"],
        channel_name=name,
    )
    await state.clear()
    await message.answer(
        texts.CHANNEL_ADDED.format(
            name=esc(channel.channel_name),
            id=esc(channel.channel_id),
            url=esc(channel.channel_url),
        ),
        reply_markup=channels_menu_keyboard(),
    )


@router.callback_query(F.data == CD["channel_list"])
async def on_channel_list(callback: CallbackQuery, db: Database) -> None:
    """Show all required channels with per-row delete buttons."""
    await callback.answer()
    if callback.message is None:
        return
    channels = await db.list_channels()
    await callback.message.edit_text(
        _render_channels(channels),
        reply_markup=channels_list_keyboard(channels),
    )


@router.callback_query(F.data.startswith(f"{CD['channel_delete']}:"))
async def on_channel_delete(callback: CallbackQuery, db: Database) -> None:
    channel_id = callback.data.split(":", 1)[1]
    await db.delete_channel(channel_id)
    await callback.answer(texts.CHANNEL_DELETED)
    if callback.message is None:
        return
    channels = await db.list_channels()
    await callback.message.edit_text(
        _render_channels(channels),
        reply_markup=channels_list_keyboard(channels),
    )


# ---------------------------------------------------------------------- #
# Back-to-panel / noop
# ---------------------------------------------------------------------- #
@router.callback_query(F.data == CD["to_admin"])
async def on_back_to_admin(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    if callback.message is None:
        return
    try:
        await callback.message.edit_text(texts.PANEL_TEXT)
    except Exception:
        await callback.message.answer(texts.PANEL_TEXT, reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "noop")
async def on_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "cancel_inline")
async def on_inline_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle inline cancel button - clear state and return to admin panel."""
    await state.clear()
    await callback.answer()
    if callback.message is None:
        return
    try:
        await callback.message.edit_text(texts.PANEL_TEXT, reply_markup=to_admin_panel_keyboard())
    except Exception:
        await callback.message.answer(texts.PANEL_TEXT, reply_markup=admin_main_keyboard())