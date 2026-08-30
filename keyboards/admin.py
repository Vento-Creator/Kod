from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional

class AdminKeyboards:
    """Admin panel keyboards"""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Main admin menu"""
        buttons = [
            [InlineKeyboardButton("🎬 Video yuklash", callback_data="admin_upload")],
            [InlineKeyboardButton("📋 Video boshqarish", callback_data="admin_manage")],
            [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")],
            [InlineKeyboardButton("📢 Xabar yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("⚙️ Kanallarni boshqarish", callback_data="admin_channels")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back")]
        ]
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def manage_movies(movies: List[dict], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
        """Movie management keyboard with pagination"""
        buttons = []
        
        start_idx = page * per_page
        end_idx = start_idx + per_page
        current_movies = movies[start_idx:end_idx]
        
        for movie in current_movies:
            buttons.append([
                InlineKeyboardButton(
                    f"🎬 {movie['code']} - {movie['caption'][:20] if movie['caption'] else 'No caption'}",
                    callback_data=f"movie_edit_{movie['code']}"
                )
            ])
        
        # Pagination
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"movies_page_{page-1}"))
        
        if end_idx < len(movies):
            nav_buttons.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"movies_page_{page+1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        buttons.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="admin_main")])
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def movie_actions(code: int) -> InlineKeyboardMarkup:
        """Actions for a specific movie"""
        buttons = [
            [InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"movie_edit_caption_{code}")],
            [InlineKeyboardButton("🔄 Kod o'zgartirish", callback_data=f"movie_edit_code_{code}")],
            [InlineKeyboardButton("🗑 O'chirish", callback_data=f"movie_delete_{code}")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_manage")]
        ]
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def user_management(users: List[dict], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
        """User management keyboard with pagination"""
        buttons = []
        
        start_idx = page * per_page
        end_idx = start_idx + per_page
        current_users = users[start_idx:end_idx]
        
        for user in current_users:
            status = "🔴" if user['is_blocked'] else "🟢"
            username = user['username'] or "No username"
            buttons.append([
                InlineKeyboardButton(
                    f"{status} {username} (ID: {user['telegram_id']})",
                    callback_data=f"user_manage_{user['telegram_id']}"
                )
            ])
        
        # Pagination
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"users_page_{page-1}"))
        
        if end_idx < len(users):
            nav_buttons.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"users_page_{page+1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        buttons.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="admin_main")])
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def user_actions(telegram_id: int, is_blocked: bool) -> InlineKeyboardMarkup:
        """Actions for a specific user"""
        action = "🔓 Blokdan olish" if is_blocked else "🔒 Bloklash"
        buttons = [
            [InlineKeyboardButton(action, callback_data=f"user_block_{telegram_id}")],
            [InlineKeyboardButton("📊 Faoliyat", callback_data=f"user_activity_{telegram_id}")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_users")]
        ]
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def confirm_action(action: str, item_id: int) -> InlineKeyboardMarkup:
        """Confirmation keyboard for destructive actions"""
        buttons = [
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm_{action}_{item_id}"),
                InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_action")
            ]
        ]
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def back_to_main() -> InlineKeyboardMarkup:
        """Simple back to main menu button"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Asosiy menyu", callback_data="admin_main")]
        ])
    
    @staticmethod
    def channel_management(channels: List[dict], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
        """Channel management keyboard with pagination"""
        buttons = []
        
        start_idx = page * per_page
        end_idx = start_idx + per_page
        current_channels = channels[start_idx:end_idx]
        
        for channel in current_channels:
            buttons.append([
                InlineKeyboardButton(
                    f"📢 {channel['channel_name']}",
                    callback_data=f"channel_view_{channel['channel_id']}"
                )
            ])
        
        # Pagination
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"channels_page_{page-1}"))
        
        if end_idx < len(channels):
            nav_buttons.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"channels_page_{page+1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        buttons.append([InlineKeyboardButton("➕ Kanal qo'shish", callback_data="channel_add")])
        buttons.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="admin_main")])
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def channel_actions(channel_id: str) -> InlineKeyboardMarkup:
        """Actions for a specific channel"""
        buttons = [
            [InlineKeyboardButton("🗑 O'chirish", callback_data=f"channel_delete_{channel_id}")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_channels")]
        ]
        return InlineKeyboardMarkup(buttons)
