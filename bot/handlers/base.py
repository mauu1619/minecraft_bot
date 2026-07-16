from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import CB_CANCEL, CB_MENU, get_admin_main_menu
from bot.texts.ru import t

router = Router(name=__name__)


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start_menu(message: Message):
    await message.answer(t.menu_title, reply_markup=get_admin_main_menu())


@router.callback_query(F.data == CB_CANCEL)
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback.message, Message):
        return

    await state.clear()

    await callback.message.edit_text(
        t.action_canceled, reply_markup=get_admin_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == f"{CB_MENU}:open")
async def cb_menu_open(callback: CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback.message, Message):
        return

    await state.clear()

    await callback.message.edit_text(t.menu_title, reply_markup=get_admin_main_menu())
    await callback.answer()
