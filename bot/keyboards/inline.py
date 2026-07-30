from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Callback prefixes --------------------------------------------
# Формат: "<ns>:<action>[:<arg>]"
CB_MENU = "menu"
CB_SERVER = "srv"
CB_WORLD = "wrd"
CB_CANCEL = "cancel"


# --- Главное меню -------------------------------------------------


def get_admin_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="🚀 Запустить", callback_data=f"{CB_SERVER}:start")
    builder.button(text="🛑 Остановить", callback_data=f"{CB_SERVER}:stop")
    builder.button(text="🔄 Перезапустить", callback_data=f"{CB_SERVER}:restart")
    builder.button(text="❓ Статус сервера", callback_data=f"{CB_SERVER}:status")
    builder.button(text="🌐 Мои миры", callback_data=f"{CB_WORLD}:list")

    builder.adjust(2, 1, 1, 1)

    return builder.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="« В меню", callback_data=f"{CB_MENU}:open")

    return builder.as_markup()


# --- Миры ----------------------------------------------------------


def get_worlds_list_keyboard(worlds_list: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for world in worlds_list:
        builder.button(text=f"🌍 {world}", callback_data=f"{CB_WORLD}:open:{world}")

    builder.button(text="« В меню", callback_data=f"{CB_MENU}:open")
    builder.adjust(1)

    return builder.as_markup()


def get_world_card(world: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="🔄 Сделать активным", callback_data=f"{CB_WORLD}:swap:{world}")
    builder.button(text="💾 Архивировать мир", callback_data=f"{CB_WORLD}:zip:{world}")
    builder.button(
        text="✍🏼 Сменить название", callback_data=f"{CB_WORLD}:rename:{world}"
    )
    builder.button(
        text="⚙️ Изменить настройки", callback_data=f"{CB_WORLD}:edit:{world}"
    )
    builder.button(text="🗑 Удалить мир", callback_data=f"{CB_WORLD}:del:{world}")
    builder.button(text="« К списку", callback_data=f"{CB_WORLD}:list")

    builder.adjust(1)

    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Отмена", callback_data=CB_CANCEL)

    return builder.as_markup()


def confirm_delete_world(world: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❗️ Да, удалить", callback_data=f"{CB_WORLD}:del_ok:{world}")
    builder.button(text="🔙 Отмена", callback_data=CB_CANCEL)
    builder.adjust(1)

    return builder.as_markup()


def confirm_change_world(world: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🌍 Да, сменить", callback_data=f"{CB_WORLD}:swap_ok:{world}")
    builder.button(text="🔙 Отмена", callback_data=CB_CANCEL)
    builder.adjust(1)

    return builder.as_markup()


def confirm_archive_world(world: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💾 Да, архивировать", callback_data=f"{CB_WORLD}:zip_ok:{world}"
    )
    builder.button(text="🔙 Отмена", callback_data=CB_CANCEL)
    builder.adjust(1)

    return builder.as_markup()
