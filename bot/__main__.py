import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from bot.config import get_settings
from bot.handlers.admin import router as admin_router

settings = get_settings()


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(admin_router)

    session = AiohttpSession(proxy=settings.proxy) if settings.proxy else None

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
