import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from loguru import logger

from bot.config import get_settings
from bot.handlers import base_router, server_router, world_router

settings = get_settings()


def setup_logging():
    logger.remove()

    logger.add(
        sys.stderr,
        level=settings.log_level,
        backtrace=False,
        diagnose=False,
        colorize=True,
        enqueue=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> "
            "<level>{level: <8}</level> "
            "<cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
        ),
    )


async def main() -> None:
    setup_logging()

    dp = Dispatcher()
    dp.include_router(base_router)
    dp.include_router(server_router)
    dp.include_router(world_router)

    session = AiohttpSession(proxy=settings.http_proxy) if settings.http_proxy else None

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )

    me = await bot.get_me()
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started @{} ({})", me.username, me.id)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
