from aiogram.fsm.state import StatesGroup, State

class ProductSearch(StatesGroup):
    title = State()

class AdminAddProduct(StatesGroup):
    title = State()
    desc = State()
    price = State()
    image_url = State()