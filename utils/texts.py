"""All user-facing and admin-facing strings for the bot (in O'zbek).

Centralizing the copy here keeps handlers / keyboards declarative and makes
adding new locales trivial later on. Every public constant is rendered with
HTML parse mode.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone


# --------------------------------------------------------------------------- #
# Escaping / formatting helpers
# --------------------------------------------------------------------------- #
def esc(text: str | None) -> str:
    """Escape arbitrary text for safe HTML rendering."""
    if text is None:
        return ""
    return html.escape(text, quote=False)


def fmt_time_remaining(ban_until) -> str:
    """Human friendly "qolgan vaqt" for an active temporary ban."""
    if ban_until is None:
        return "cheksiz"
    now = datetime.now(timezone.utc)
    delta = ban_until - now
    if delta.total_seconds() <= 0:
        return "tugadi"
    total_minutes = max(1, int(delta.total_seconds() // 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours} soat {minutes} minut"
    return f"{minutes} minut"


# --------------------------------------------------------------------------- #
# Common / home
# --------------------------------------------------------------------------- #
BOT_NAME = "🎬 Kodli Bot"

START_USER = (
    "🎬 <b>Kodli Bot</b> — eng yaxshi kino qidiruvchi bot!\n\n"
    "Sizga kerakli kinoning <b>raqamli kodini</b> menga yuboring — "
    "darhol kinoni oling!\n\n"
    "Masalan: <code>12345</code>\n\n"
    "Kodingizni @kodli_bot kanalida topishingiz mumkin."
)

HELP_TEXT = (
    "ℹ️ <b>Foydalanish yo'riqnoma</b>\n\n"
    "1. Kerakli kinoning raqamli kodini oling.\n"
    "2. Kodni shu yerga xabar sifatida yuboring.\n"
    "3. Kino tezkorlik bilan yetkazib beriladi 🎬\n\n"
    "⚠️ Juda ko'p so'rov yuborsangiz, vaqtincha cheklangan bo'lishingiz mumkin."
)

NOT_FOUND_TEXT = (
    "🤷‍♂️ <b>Bunday kodli kino topilmadi</b>: <code>{code}</code>.\n\n"
    "Kodni tekshirib qaytadan yuboring."
)

FAILED_MEDIA_TEXT = (
    "⚠️ <code>{code}</code> kodli kinoning video-fayli hozirda "
    "mavjud emas. Keyinroq qayta urinib ko'ring."
)

INVALID_CODE_TEXT = (
    "⚠️ Iltimos, faqat <b>raqamlardan</b> iborat kod yuboring "
    "(masalan, <code>12345</code>)."
)

SEARCH_PROMPT = (
    "🔍 <b>Kino qidirish</b>\n\n"
    "Kerakli kinoning <b>raqamli kodini</b> yuboring.\n\n"
    "Masalan: <code>12345</code>"
)

DIGITS_ONLY = "Kod faqat raqamlardan iborat bo'lishi kerak (probelsiz)."

# Inline keyboard labels
BTN_SEARCH_AGAIN = "🔍 Boshqa kino qidirish"
BTN_HOME = "🏠 Bosh menyu"
BTN_BACK = "⬅️ Orqaga"
BTN_HOME_INLINE = "🏠 Bosh menyu"
BTN_CANCEL = "❌ Bekor qilish"

CANCELLED = "❌ <b>Amal bekor qilindi.</b>\n\nJoriy harakat to'xtatildi."
CANCEL_HELP = (
    "❌ Bekor qilish uchun tugmani bosing yoki <code>/cancel</code> buyrug'ini yuboring."
)


# --------------------------------------------------------------------------- #
# Admin panel
# --------------------------------------------------------------------------- #
PANEL_TEXT = (
    "🛠️ <b>Admin panel</b>\n\n"
    "• <b>Yuklash</b> – yangi kino qo'shish (fayl -> caption -> kod)\n"
    "• <b>Kod qidirish</b> – kino ko'rish / tahrirlash / o'chirish\n"
    "• <b>Foydalanuvchilar</b> – bloklash, blokdan chiqarish, faoliyat\n"
    "• <b>Eshek</b> – xabar tarqatish\n"
    "• <b>Statistika</b> – ko'rsatkichlar\n\n"
    "Quyidagi menyudan amalni tanlang."
)

STATS_TEXT = (
    "📊 <b>Statistika</b>\n\n"
    "👥 Foydalanuvchilar:  {users}\n"
    "🎬 Kinolar (jami):   {movies}\n"
    "✅ Kinolar (faol):   {active_movies}\n"
    "🔍 Qidiruvlar:       {searches}\n"
)

MOVIE_CARD = (
    "🎬 <b>Kino</b>\n\n"
    "📢 Kod:      <code>{code}</code>\n"
    "🗃 Turi:      {file_type}\n"
    "📝 Caption:   {caption}\n"
    "📊 Holat:     {status}\n"
    "🕐 Qo'shildi:  {created}\n"
)

USER_LINE = (
    "{index}. <b>{name}</b>\n"
    "   🆔 <code>{tgid}</code> · {badge}\n"
    "   ⚠️ Ogohlantirish: {warnings}"
)

USERS_HEADER = "👥 <b>Foydalanuvchilar</b>\n\n"
USERS_EMPTY = "👥 <b>Foydalanuvchilar</b>\n\n<i>Hali hech kim yo'q.</i>"
USER_NOT_FOUND = "🤷‍♂️ <b>{identifier}</b> uchun foydalanuvchi topilmadi."
USER_ACTIVITY_HEADER = "🗂 <b>Faoliyat: {name}</b>\n🆔 {tgid}\n\n{lines}"
USER_ACTIVITY_EMPTY = "<i>Hali so'rov yo'q.</i>"

NO_SUCH_MOVIE = "⚠️ Bu kino endi mavjud emas."
CAPTION_UPDATED = "✅ <b>Caption yangilandi</b>\n\n{card}"
CODE_UPDATED = "✅ <b>Kod yangilandi</b>\n\n{card}"
PERMANENTLY_DELETED = "💥 <b>Kino butunlay o'chirildi.</b>"
HARD_DELETE_PROMPT = (
    "💣 <b>Ishengiz?</b>\n\n"
    "Bu kino satrini ma'lumotlar bazasidan <b>butunlay o'chiradi</b>. "
    "Buni bekor qilib bo'lmaydi."
)
CANNOT_REPLAY_MEDIA = "⚠️ Media-faylni (eskirgan file_id?) qayta yuborib bo'lmaydi."

# Upload flow
UPLOAD_STEP1 = (
    "⬆️ <b>Yuklash bosqichi 1/3</b>\n\n"
    "Endi <b>video faylni</b> yuboring "
    "(video, GIF, audio, hujjat yoki foto ham qabul qilinadi)."
)
UPLOAD_MEDIA_RECEIVED = (
    "📎 <b>Fayl qabul qilindi!</b>\n\n"
    "Aniqlangan caption:\n\n<i>{caption}</i>\n\n"
    "Nima deb saqlaymiz?"
)
UPLOAD_NO_MEDIA = "⚠️ Iltimos, <b>video</b> (yoki boshqa media) yuboring, matn emas."
UPLOAD_NO_CAPTION_MSG = "📎 <b>Fayl qabul qilindi!</b>\n\nFayl bilan caption birikkan emas. Endi caption matnini yuboring yoki tugmalardan birini bosing."
UPLOAD_STEP3_CODE = (
    "🔢 <b>Bosqachi 3/3 - kod</b>\n\n"
    "Kod <b>faqat raqamlardan</b> iborat, probelsiz, <b>noyob</b> bo'lishi kerak.\n"
    "Masalan: <code>12345</code>"
)
CODE_TAKEN = "⚠️ Kod <code>{code}</code> allaqachon <b>band</b>.\n\nBoshqa kod kiriting:"
CODE_INVALID = "⚠️ {error}\n\nQayta urinib ko'ring:"

# Caption editing
EDIT_CAPTION_PROMPT = (
    "✏️ Bu kinoning <b>yangi captionini</b> yuboring "
    "(bekor qilish uchun ❌ Bekor qilish).\n\n"
    "<i>Bo'sh xabar captionni tozalaydi.</i>"
)
EDIT_CAPTION_EMPTY_PROMPT = (
    "✍️ <b>Yangi caption matnini</b> yuboring (bekor uchun ❌ Bekor qilish)."
)
EDIT_CODE_PROMPT = (
    "🔁 Bu kinoning <b>yangi raqamli kodini</b> yuboring "
    "(bekor qilish uchun ❌ Bekor qilish)."
)

# Media replacement
MEDIA_REPLACE_PROMPT = (
    "🖼️ <b>Media almashtirish</b>\n\n"
    "Endi kinoning <b>yangi media faylini</b> yuboring "
    "(video, GIF, audio, hujjat yoki foto).\n\n"
    "Eski media o'chiriladi, yangi media o'rniga qo'yiladi."
)
NO_MEDIA_ERROR = "⚠️ Iltimos, <b>media faylni</b> yuboring (video, GIF, audio, hujjat yoki foto)."

# User management
USER_FIND_PROMPT = "🔍 Foydalanuvchining <b>Telegram id</b> yoki <b>@username</b> ni yuboring:"
USER_FIND_NOT_FOUND = "🤷‍♂️ <code>{identifier}</code> uchun foydalanuvchi topilmadi."

# Broadcast
BROADCAST_START = (
    "📣 <b>Eshek</b>\n\n"
    "Xabarni matnini yuboring — u barcha faol foydalanuvchilarga "
    "yetkazib beriladi.\n\n"
    "<i>HTML avtomatik escaped.</i>"
)
BROADCAST_EMPTY = "⚠️ Habar matni bo'sh bo'lmasligi kerak."
BROADCAST_SENDING = "📣 Tarqatilyapti... bu bir oz kuting."
BROADCAST_DONE = (
    "📣 <b>Eshek yakunlandi</b>\n\n"
    "👥 Jami:      {total}\n"
    "✅ Yetkazildi: {sent}\n"
    "❌ Xatolar:    {failed}\n"
    "🚫 Bloklangan:{newly_blocked}\n"
)

# Force-subscribe (channels) - admin
CHANNELS_MENU = (
    "📢 <b>Kanallarni boshqarish</b>\n\n"
    "Majburiy obuna kanallari: foydalanuvchilar kino qidirishdan oldin "
    "quyidagi kanallarga obuna bo'lishi shart.\n\n"
    "Tanlang:"
)
CHANNEL_ADD_STEP_ID = (
    "🔢 <b>Kanal qo'shish (1/3)</b>\n\n"
    "Kanalning <b>ID raqamini</b>, <b>@username</b> yoki <b>linkini</b> yuboring.\n"
    "Masalan: <code>-1001234567890</code>, <code>@kanalnomi</code> yoki "
    "<code>https://t.me/kanalnomi</code>\n\n"
    "Agar faqat raqam yuborsangiz, avtomatik <code>-100</code> qo'shiladi."
)
CHANNEL_ADD_STEP_LINK = (
    "🔗 <b>Kanal qo'shish (2/3)</b>\n\n"
    "Endi kanalning <b>invite-linkini</b> yuboring.\n"
    "Masalan: <code>https://t.me/+abc123xyz</code>"
)
CHANNEL_ADD_STEP_NAME = (
    "🏷️ <b>Kanal qo'shish (3/3)</b>\n\n"
    "Endi kanalning <b>nomini</b> yuboring."
)
CHANNEL_ADDED = (
    "✅ <b>Kanal qo'shildi!</b>\n\n"
    "🏷️ Nom:  {name}\n"
    "🆔 ID:    {id}\n"
    "🔗 Link:  {url}"
)
CHANNEL_ADD_INVALID_ID = "⚠️ Kanal ID noto'g'ri. ID raqam, @username yoki https://t.me/... linki bo'lishi kerak."
CHANNEL_ADD_INVALID_LINK = "⚠️ Link <b>https://t.me/...</b> ko'rinishida bo'lishi kerak."
CHANNEL_ADD_INVALID_NAME = "⚠️ Kanal nomi bo'sh bo'lmasligi kerak."
CHANNEL_DUPLICATE_ID = "⚠️ Bu kanal allaqachon <b>qo'shilgan</b>."
CHANNELS_EMPTY = "📋 <b>Kanallar ro'yxati</b>\n\n<i>Hali hech qanday kanal qo'shilmagan.</i>"
CHANNELS_LIST = "📋 <b>Kanallar ro'yxati</b>\n\n{lines}"
CHANNEL_DELETED = "Kanal o'chirildi ✔️"

# Media catalog
MOVIES_CATALOG_MENU = (
    "📚 <b>Barcha kinolar</b>\n\n"
    "Barcha kinolarni ko'rish, tahrirlash va boshqarish uchun "
    "ro'yxatdan foydalaning."
)
MOVIES_EMPTY = "📚 <b>Kinolar ro'yxati</b>\n\n<i>Hali hech qanday kino qo'shilmagan.</i>"

# Force-subscribe - user side
SUB_REQUIRED = (
    "🔒 <b>Majburiy obuna!</b>\n\n"
    "Kino qidirishni boshlashdan oldin quyidagi kanallarga "
    "obuna bo'lishingiz kerak:\n\n"
    "{channels}\n\n"
    "Obuna bo'lgach, \"✅ Tekshirish\" tugmasini bosing."
)
SUB_BANNED_BOT_ACCESS = "⚠️ Bot kanalga to'liq kira olmayapti. Admin interfeysidan kanalni tekshiring."
SUB_CHANNEL_UNCHECKABLE = (
    "⚠️ <b>Bot quyidagi kanallardagi obunangizni tekshira olmadi:</b>\n"
    "{channels}\n\n"
    "Sabab: kanal <b>ID</b> noto'g'ri kiritilgan yoki <b>bot kanalga admin "
    "qilib qo'shilmagan</b>. Iltimos, administratorga xabar bering."
)
SUB_SUCCESS = "✅ <b>Obuna muvaffaqiyatli tasdiqlandi!</b>\n\nEndi kino kodini yuboring."
SUB_STILL_MISSING = (
    "⚠️ Hali ham quyidagi kanallarga obuna bo'lishingiz kerak:\n\n"
    "{channels}"
)

# Flood / anti-spam (O'zbek)
FLOOD_WARNING = (
    "⚠️ <b>Birinchi ogohlantirish - so'rovlar juda ko'p!</b>\n\n"
    "⏱️ So'rovlaringiz juda tez - sekinlating!\n\n"
    "<b>Keyingi buzilish uchun avtomatik vaqtincha blok.</b>"
)
FLOOD_TEMP_BAN = (
    "⛔ <b>Spam uchun vaqtincha blok</b>\n"
    "Buzilish soni: {level}\n"
    "Muddat: {minutes} minut (~{time_left})\n"
    "Keyingi safar kino qidirmoqchi bo'lsangiz, {time_left} so'ng qayta urinib ko'ring."
)
FLOOD_PERMANENT = (
    "🚫 <b>Robotga takroriy spam yuborlaganingiz sababli "
    "doimiy bloklandingiz.</b>"
)
FLOOD_BANNED = "🚫 Siz botda blokstatusga ega ekansiz. Xabarlar chetlatildi."