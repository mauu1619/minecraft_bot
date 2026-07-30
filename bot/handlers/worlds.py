import asyncio
import contextlib
import re
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from loguru import logger

from bot.config import get_settings
from bot.exceptions import MinecraftBotError
from bot.filters.is_admin import AdminFilter
from bot.keyboards.inline import (
    CB_WORLD,
    back_to_menu,
    cancel_keyboard,
    confirm_archive_world,
    confirm_change_world,
    confirm_delete_world,
    get_world_card,
    get_worlds_list_keyboard,
)
from bot.services.server import RconCredentials, ServerService
from bot.services.worlds import WorldsService
from bot.states.worlds import WorldCreation, WorldRenaming
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
    service_name=settings.minecraft_service_name,
    game_port=settings.server_port,
)


@router.callback_query(F.data == f"{CB_WORLD}:list")
async def cb_show_worlds_list(callback: CallbackQuery) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return

    worlds = await worlds_service.get_available_worlds()
    if not worlds:
        await callback.answer(t.no_worlds_found, show_alert=True)
        return

    await callback.message.edit_text(
        "🌐 Мои миры", reply_markup=get_worlds_list_keyboard(worlds)
    )

    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB_WORLD}:open:"))
async def cb_world_action_ask(callback: CallbackQuery) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return

    world = callback.data.rsplit(":", 1)[-1]

    is_running = await server_service.is_service_running()
    cur_world = await worlds_service.get_current_world()
    if cur_world == world and is_running:
        is_active = True
    else:
        is_active = False

    await callback.message.edit_text(
        t.world_card.format(world=world, status="✅" if is_active else "❌"),
        reply_markup=get_world_card(world),
    )

    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB_WORLD}:swap:"))
@router.callback_query(F.data.startswith(f"{CB_WORLD}:zip:"))
@router.callback_query(F.data.startswith(f"{CB_WORLD}:del:"))
async def cb_universal_action_ask(callback: CallbackQuery) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return

    _, action, world = callback.data.split(":")

    match action:
        case "swap":
            text = t.world_switch_confirm.format(world_name=world)
            kb = confirm_change_world
        case "zip":
            text = t.world_archive_confirm.format(world_name=world)
            kb = confirm_archive_world
        case "del":
            text = t.world_delete_confirm.format(world_name=world)
            kb = confirm_delete_world
        case _:
            return

    await callback.message.edit_text(text, reply_markup=kb(world))

    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB_WORLD}:swap_ok:"))
@router.callback_query(F.data.startswith(f"{CB_WORLD}:zip_ok:"))
@router.callback_query(F.data.startswith(f"{CB_WORLD}:del_ok:"))
async def cb_world_action_ok(callback: CallbackQuery) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return

    await callback.answer()

    _, action, world = callback.data.rsplit(":", 2)

    try:
        match action.split("_")[0]:
            case "swap":
                await callback.message.edit_text(
                    t.world_changing_process.format(world_name=world),
                )
                await worlds_service.change_world_name(world)
                await server_service.restart_server()

                msg = t.world_change_success

            case "zip":
                await callback.message.edit_text(
                    t.world_archiving_process.format(world_name=world)
                )

                is_active = await worlds_service.get_current_world() == world
                is_running = await server_service.is_service_running()
                if is_active and is_running:
                    async with server_service.hold_world_saving():
                        archive_path = await worlds_service.export_world(world)
                else:
                    archive_path = await worlds_service.export_world(world)

                await callback.message.answer_document(FSInputFile(archive_path))
                archive_path.unlink(missing_ok=True)

                msg = t.world_archive_sucess

            case "del":
                await callback.message.edit_text(t.world_deleting_process)
                await worlds_service.delete_world(world)

                msg = t.world_delete_success

            case _:
                return

    except MinecraftBotError as exc:
        await callback.message.edit_text(
            t.error_message.format(error=str(exc)), reply_markup=back_to_menu()
        )

    else:
        await callback.message.edit_text(
            msg.format(world_name=world), reply_markup=back_to_menu()
        )


@router.callback_query(F.data == f"{CB_WORLD}:new")
async def cb_world_creation_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback.message, Message):
        return

    await state.set_state(WorldCreation.waiting_for_world_name)

    prompt = await callback.message.answer(
        t.world_creation_prompt, reply_markup=cancel_keyboard()
    )

    await state.update_data(prompt_msg=prompt)

    await callback.answer()


@router.message(WorldCreation.waiting_for_world_name, F.text)
async def cb_world_creation_end(message: Message, state: FSMContext) -> None:
    if message.text is None:
        await state.clear()
        return

    world_name = message.text.strip().lower().replace(" ", "_")

    if not re.match(r"^[a-zA-Z0-9_]{1,40}$", world_name):
        await message.answer(t.world_invalid_name)
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

    except MinecraftBotError as exc:
        await msg.edit_text(
            t.error_message.format(error=str(exc)), reply_markup=back_to_menu()
        )


@router.callback_query(F.data.startswith(f"{CB_WORLD}:rename:"))
async def cb_rename_world_start(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        return

    await state.set_state(WorldRenaming.waiting_for_new_name)

    world = callback.data.rsplit(":", 1)[-1]

    prompt = await callback.message.edit_text(
        t.world_renaming_prompt.format(world_name=world), reply_markup=cancel_keyboard()
    )

    await state.update_data(old_name=world, prompt_msg=prompt)

    await callback.answer()


@router.message(WorldRenaming.waiting_for_new_name, F.text)
async def cb_world_renaming_end(message: Message, state: FSMContext) -> None:
    if message.text is None:
        await state.clear()
        return

    new_name = message.text.strip().lower().replace(" ", "_")

    if not re.match(r"^[a-zA-Z0-9_]{1,40}$", new_name):
        await message.answer(t.world_invalid_name)
        return

    data = await state.get_data()
    old_name = data.get("old_name")
    prompt_msg = data.get("prompt_msg")

    if old_name is None or prompt_msg is None:
        logger.error("Данные не были получены из FSM словаря")
        await message.answer(
            t.error_message.format(error="Непредвиденная ошибка!\nПопробуйте еще раз:"),
        )
        raise IndexError

    if new_name == old_name:
        await message.answer(t.world_same_name)
        return

    await state.clear()

    msg = await message.answer(
        t.world_renaming_process.format(old_name=old_name, new_name=new_name)
    )

    await asyncio.sleep(1)
    restart = False

    try:
        is_active = await worlds_service.get_current_world() == old_name
        is_running = await server_service.is_service_running()
        if is_active and is_running:
            await server_service.stop_server(restart=True)
            restart = True

        await worlds_service.rename_world(world=old_name, new_name=new_name)
        await server_service.start_server(start_ok=True)
        await msg.edit_text(
            t.world_renaming_success.format(
                "\n🔄 Сервер успешно перезапущен!" if restart else ""
            )
        )
    except MinecraftBotError as exc:
        await msg.edit_text(t.error_message.format(error=str(exc)))

    await asyncio.sleep(3)
    with contextlib.suppress(TelegramBadRequest):
        prompt_msg.delete()
        message.delete()
        msg.delete()
