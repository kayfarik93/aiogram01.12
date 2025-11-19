from aiogram.fsm.state import StatesGroup, State

class RegisterUser(StatesGroup):
    name = State()
    email = State()


class UpdateUser(StatesGroup):
    id = State()
    name = State()
    email = State()


class GetUser(StatesGroup):
    id = State()


class DeleteUser(StatesGroup):
    id = State()
