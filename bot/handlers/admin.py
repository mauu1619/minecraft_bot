from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.filters.admin import AdminFilter
from bot.keyboards.admin import get_admin_main_menu
from bot.services.minecraft import restart_server, start_server, stop_server
from bot.services.system import is_server_running
from bot.texts.ru import t

router = Router(name="admin_handler")
router.callback_query.filter(AdminFilter())
router.message.filter(AdminFilter())

SERVER_ACTIONS = {
    "start": {
        "func": start_server,
        "process_text": t.server_starting,
        "success_text": t.server_started,
    },
    "stop": {
        "func": stop_server,
        "process_text": t.server_stopping,
        "success_text": t.server_stopped,
    },
    "restart": {
        "func": restart_server,
        "process_text": t.server_restarting,
        "success_text": t.server_restarted,
    },
}


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start_menu(message: Message):
    await message.answer(t.menu_title, reply_markup=get_admin_main_menu())


@router.callback_query(F.data.endswith(":server"))
async def cb_universal_server(callback: CallbackQuery):
    action = callback.data.split(":")[0]

    if action not in SERVER_ACTIONS:
        return

    action_data = SERVER_ACTIONS[action]
    func = action_data["func"]

    if action in ("stop", "restart") and not is_server_running():
        await callback.message.answer("Сервер не запущен!!!")
        await callback.answer()
        return
    await callback.message.edit_text(action_data["process_text"])

    result, _, error = await func()

    if result:
        await callback.message.edit_text(action_data["success_text"])
    else:
        await callback.message.edit_text(t.error_message.format(error=error))

    await callback.message.answer(t.menu_title, reply_markup=get_admin_main_menu())
    await callback.answer()


@router.message(Command("start_server", "stop_server", "restart_server"))
async def cmd_universal_server(message: Message, command: CommandObject):
    action = command.command.split("_")[0]

    action_data = SERVER_ACTIONS["action"]
    func = action_data["func"]

    if action in ("stop", "restart") and not is_server_running():
        await message.answer("Сервер не запущен!!!")
        return
    await message.answer(action_data["process_text"])

    result, _, error = await func()

    if result:
        await message.answer(action_data["success_text"])
    else:
        await message.answer(t.error_message.format(error=error))

    await message.answer(t.menu_title, reply_markup=get_admin_main_menu())
