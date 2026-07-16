import asyncio
import contextlib
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from loguru import logger

from bot.config import get_settings
from bot.exceptions import RconConnectionError, ServerError
from bot.filters.is_admin import AdminFilter
from bot.keyboards.inline import CB_SERVER, back_to_menu
from bot.services.server import RconCredentials, ServerService, ServerState
from bot.texts.ru import t

router = Router(name=__name__)
router.callback_query.filter(AdminFilter())
router.message.filter(AdminFilter())

settings = get_settings()

server_service = ServerService(
    rcon_creds=RconCredentials(
        password=settings.rcon_password, port=settings.rcon_port
    ),
    server_dir=Path(settings.minecraft_server_dir),
)

SERVER_ACTIONS = {
    "start": {
        "func": server_service.start_server,
        "process_text": t.server_starting,
        "success_text": t.server_started,
    },
    "stop": {
        "func": server_service.stop_server,
        "process_text": t.server_stopping,
        "success_text": t.server_stopped,
    },
    "restart": {
        "func": server_service.restart_server,
        "process_text": t.server_restarting,
        "success_text": t.server_restarted,
    },
}


@router.callback_query(
    F.data.in_({f"{CB_SERVER}:start", f"{CB_SERVER}:stop", f"{CB_SERVER}:restart"})
)
async def cb_universal_server(callback: CallbackQuery):
    if not callback.data:
        return

    action = callback.data.split(":")[-1]

    if action not in SERVER_ACTIONS:
        logger.warning("Неизвестное действие: {}", action)
        return

    if not isinstance(callback.message, Message):
        return

    action_data = SERVER_ACTIONS[action]
    func = action_data["func"]

    if action in ("stop", "restart") and not await server_service._is_service_running():
        await callback.message.answer(t.status_offline)
        await callback.answer()
        return
    await callback.message.edit_text(action_data["process_text"])

    await asyncio.sleep(1)

    try:
        await func()
    except (ServerError, RconConnectionError) as exc:
        await callback.message.edit_text(
            t.error_message.format(error=str(exc)), reply_markup=back_to_menu()
        )
    else:
        await callback.message.edit_text(
            action_data["success_text"], reply_markup=back_to_menu()
        )

    await callback.answer()


@router.message(Command("start_srv", "stop_srv", "restart_srv"))
async def cmd_universal_server(message: Message, command: CommandObject):
    action = command.command.split("_")[0]

    action_data = SERVER_ACTIONS[action]
    func = action_data["func"]

    if action in ("stop", "restart") and not await server_service._is_service_running():
        await message.answer(t.status_offline, reply_markup=back_to_menu())
        return
    msg = await message.answer(action_data["process_text"])

    await asyncio.sleep(1)

    try:
        await func()
    except (ServerError, RconConnectionError) as exc:
        await msg.edit_text(
            t.error_message.format(error=str(exc)), reply_markup=back_to_menu()
        )
    else:
        await msg.edit_text(action_data["success_text"], reply_markup=back_to_menu())


@router.message(Command("status"))
@router.callback_query(F.data == f"{CB_SERVER}:status")
async def handler_status_server(event: Message | CallbackQuery):
    server_status = await server_service.get_detailed_status()

    if isinstance(event, CallbackQuery):
        await event.answer()

        if not isinstance(event.message, Message):
            return
        target = event.message
        user_msg = None
    else:
        target = event
        user_msg = event

    match server_status.state:
        case ServerState.ONLINE:
            text = t.status_online.format(
                online=server_status.players_online,
                max=server_status.players_max,
                ping=server_status.ping,
            )
        case ServerState.OFFLINE:
            text = t.status_offline
        case ServerState.STARTING:
            text = t.status_starting

    msg = await target.answer(text)

    if user_msg:
        with contextlib.suppress(TelegramBadRequest):
            await user_msg.delete()

    await asyncio.sleep(10)
    with contextlib.suppress(TelegramBadRequest):
        await msg.delete()
