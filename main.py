"""Application entry point.

Run with::

    python main.py

Make sure `.env` exists (copy of `.env.example`) and the packages in
`requirements.txt` are installed.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from config import get_settings
from database import Database
from handlers import (
    cancel_router,
    admin_router,
    admin_users_router,
    common_router,
    errors_router,
    user_router,
)
from middlewares import AntiFloodMiddleware, DatabaseMiddleware

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def set_bot_commands(bot: Bot) -> None:
    """Fill the menu button list users see in the chat."""
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Botni boshlash"),
            BotCommand(command="help", description="Yordam"),
        ],
        scope=BotCommandScopeDefault(),
    )


async def main() -> None:
    setup_logging()
    settings = get_settings()
    logger.info("Kodli Movie Finder bot boshlatilmoqda...")

    db = Database(settings.database_path)
    await db.connect()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    db_middleware = DatabaseMiddleware(db)
    flood_middleware = AntiFloodMiddleware(db)

    dp.message.outer_middleware(flood_middleware)
    dp.callback_query.outer_middleware(flood_middleware)
    dp.message.middleware(db_middleware)
    dp.callback_query.middleware(db_middleware)

    # IMPORTANT: the global cancel router must be registered BEFORE every
    # other router. aiogram dispatches updates in registration order and the
    # first handler whose filters match consumes the update; registering the
    # cancel router first guarantees that "❌ Bekor qilish" / "/cancel" clears
    # the current FSM state before any state-specific handler (UploadStates,
    # BroadcastStates, ChannelStates, EditStates, ...) can swallow it.
    dp.include_router(cancel_router)
    # IMPORTANT: admin routers must be registered BEFORE the user router.
    # aiogram dispatches updates in registration order and the first handler
    # whose filters match consumes the update. If user_router were earlier,
    # its catch-all `generic_hint` would swallow admin Reply-Keyboard presses
    # (e.g. "⬆️ Yuklash") before the matching admin handler could run.
    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(admin_users_router)
    dp.include_router(user_router)
    dp.include_router(errors_router)

    dp.startup.register(set_bot_commands)
    dp.shutdown.register(db.close)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Polling boshlandi...")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot foydalanuvchi tomonidan to'xtatildi.")