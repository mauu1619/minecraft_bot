from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="🚀 Запустить", callback_data="start:server")
    builder.button(text="🛑 Остановить", callback_data="stop:server")
    builder.button(text="🔄 Перезапустить", callback_data="restart:server")
    builder.button(text="❓ Статус сервера", callback_data="status:server")
    builder.button(text="✨ Создать мир", callback_data="create:world")
    builder.button(text="🌍 Сменить мир", callback_data="change:world")

    builder.adjust(2, 1, 1, 2)

    return builder.as_markup()
