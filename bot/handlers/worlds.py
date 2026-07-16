import asyncio
import re
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger

from bot.config import get_settings
from bot.exceptions import MinecraftBotError, WorldAlreadyExistsError
from bot.filters.is_admin import AdminFilter
from bot.keyboards.inline import (
    CB_MENU,
    CB_WORLD,
    back_to_menu,
    cancel_world_creation,
    confirm_changing_world,
    confirm_delete_world,
    get_worlds_list_keyboard,
)
from bot.services.server import RconCredentials, ServerService
from bot.services.worlds import WorldsService
from bot.states.worlds import WorldCreation
from bot.texts.ru import t

router = Router(name=__name__)
router.callback_query.filter(AdminFilter())

settings = get_settings()

worlds_service = WorldsService(server_dir=Path(settings.minecraft_server_dir))
server_service = ServerService(
    rcon_creds=RconCredentials(
        password=settings.rcon_password, port=settings.rcon_port
    ),
    server_dir=Path(settings.minecraft_server_dir),
)


@router.callback_query(F.data.startswith(f"{CB_WORLD}:list:"))
async def cb_show_worlds_list(callback: CallbackQuery) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return

    action = callback.data.rsplit(":", 1)[-1]

    worlds = await worlds_service.get_available_worlds()
    if not worlds:
        await callback.answer(t.no_worlds_found, show_alert=True)
        return

    text = t.world_change_prompt if action == "swap" else t.world_delete_prompt
    await callback.message.edit_text(
        text, reply_markup=get_worlds_list_keyboard(worlds, action)
    )

    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB_MENU}:del:"))
@router.callback_query(F.data.startswith(f"{CB_MENU}:swap:"))
async def cb_world_action_ask(callback: CallbackQuery) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return

    _, action, world = callback.data.rsplit(":", 2)

    if action == "swap":
        text = t.world_switch_confirm
        markup = confirm_changing_world
    else:
        text = t.world_delete_confirm
        markup = confirm_delete_world

    await callback.message.edit_text(
        text.format(world_name=world), reply_markup=markup(world)
    )

    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB_WORLD}:del_ok:"))
@router.callback_query(F.data.startswith(f"{CB_WORLD}:swap_ok:"))
async def cb_world_action_ok(callback: CallbackQuery) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return

    _, action, world = callback.data.rsplit(":", 2)

    try:
        match action.split("_")[0]:
            case "swap":
                await worlds_service.change_world_name(world)
                await server_service.restart_server()
                msg_success = t.world_change_success
            case "del":
                await worlds_service.delete_world(world)
                msg_success = t.world_delete_success
            case _:
                raise MinecraftBotError(f"Неизвестное действие: {action}")

        await callback.message.edit_text(
            msg_success.format(world_name=world), reply_markup=back_to_menu()
        )
    except MinecraftBotError as exc:
        logger.exception("Ошибка во время удаления/смены мира: {}", exc)
        await callback.message.edit_text(
            t.error_message.format(error=str(exc)), reply_markup=back_to_menu()
        )

    await callback.answer()


@router.callback_query(F.data == f"{CB_WORLD}:new")
async def cb_world_creation_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback.message, Message):
        return

    await state.set_state(WorldCreation.waiting_for_world_name)

    await callback.message.answer(
        t.world_creation_prompt, reply_markup=cancel_world_creation()
    )

    await callback.answer()


@router.message(WorldCreation.waiting_for_world_name, F.text)
async def cb_world_creation_step(message: Message, state: FSMContext) -> None:
    if message.text is None:
        await state.clear()
        return

    world_name = message.text.strip().lower().replace(" ", "_")

    if not re.match(r"^[a-zA-Z0-9_]{1,40}$", world_name):
        await message.answer(t.world_creation_invalid_name)
        return

    await state.clear()

    msg = await message.answer(t.world_creating_process.format(world_name=world_name))
    await asyncio.sleep(1)

    try:
        await worlds_service.create_world(world_name)
        await server_service.restart_server()
        await msg.edit_text(
            t.world_create_success.format(world_name=world_name),
            reply_markup=back_to_menu(),
        )
    except WorldAlreadyExistsError as exc:
        await msg.edit_text(str(exc), reply_markup=back_to_menu())
    except MinecraftBotError as exc:
        await msg.edit_text(
            t.error_message.format(error=str(exc)), reply_markup=back_to_menu()
        )
