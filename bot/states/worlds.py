from aiogram.fsm.state import State, StatesGroup


class WorldCreation(StatesGroup):
    waiting_for_world_name = State()


class WorldRenaming(StatesGroup):
    waiting_for_new_name = State()
