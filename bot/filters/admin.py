from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings

settings = get_settings()


class AdminFilter(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        if user is None:
            return False
        return user.id in settings.admin_ids
