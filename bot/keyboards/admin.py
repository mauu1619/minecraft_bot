from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 Запустить сервер", callback_data="start:server"),
        InlineKeyboardButton(text="🛑 Остановить сервер", callback_data="stop:server"),
        InlineKeyboardButton(
            text="🔄 Перезапустить сервер", callback_data="restart:server"
        ),
    )
    builder.row(
        InlineKeyboardButton(text="❓ Статус сервера", callback_data="status:server"),
    )
    builder.row(
        InlineKeyboardButton(text="✨ Создать мир", callback_data="create:world"),
        InlineKeyboardButton(text="🌍 Сменить мир", callback_data="change:world"),
    )

    return builder.as_markup()
