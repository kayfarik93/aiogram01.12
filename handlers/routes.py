from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from forms import RegisterUser, UpdateUser, GetUser, DeleteUser
from client import (
    register_user,
    get_all_users,
    get_user_by_id,
    delete_user_by_id,
    update_user_by_id
)

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

router = Router()


@router.message(F.text.in_({"/start", "/add"}))
async def start(msg: Message, state: FSMContext):
    await state.set_state(RegisterUser.name)
    await msg.answer("Привет! Как тебя зовут?")


@router.message(RegisterUser.name)
async def get_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await state.set_state(RegisterUser.email)
    await msg.answer("Укажи, пожалуйста, свой email:")


@router.message(RegisterUser.email)
async def get_email(msg: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name")
    email = msg.text

    success = await register_user(name=name, email=email)

    if success:
        await msg.answer("✅ Спасибо! Ты успешно зарегистрирован.", reply_markup=ReplyKeyboardRemove())
    else:
        await msg.answer("❌ Произошла ошибка при сохранении. Попробуй позже.")

    await state.clear()


markup = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🔢 По ID", callback_data="sort:id:asc"),
            InlineKeyboardButton(text="🔠 По имени", callback_data="sort:name:asc"),
            InlineKeyboardButton(text="📧 По email", callback_data="sort:email:asc"),
        ],
        [
            InlineKeyboardButton(text="⬆️ Возрастание", callback_data="sort:current:asc"),
            InlineKeyboardButton(text="⬇️ Убывание", callback_data="sort:current:desc"),
        ]
    ]
)

# Храним текущие параметры сортировки
current_sort = {"order_by": "id", "direction": "asc"}


@router.message(F.text == "/users")
async def list_users(msg: Message):
    users = await get_all_users(order_by=current_sort["order_by"], direction=current_sort["direction"])

    if not users:
        await msg.answer("Пока что нет зарегистрированных пользователей.")
        return

    text = "<b>Зарегистрированные пользователи:</b>\n\n"
    for user in users:
        text += f"👤 <b>{user['name']}</b> — {user['email']}\n"

    await msg.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("sort:"))
async def handle_sort_callback(callback: CallbackQuery):
    parts = callback.data.split(":")
    field = parts[1]
    direction = parts[2]

    # Если "current", то сохраняем только направление, не меняя поле
    if field == "current":
        current_sort["direction"] = direction
    else:
        current_sort["order_by"] = field
        current_sort["direction"] = direction

    users = await get_all_users(order_by=current_sort["order_by"], direction=current_sort["direction"])

    if not users:
        await callback.message.edit_text("Пока что нет зарегистрированных пользователей.")
        return

    text = f"<b>Зарегистрированные пользователи (сортировка: {current_sort['order_by']} {current_sort['direction']}):</b>\n\n"
    for user in users:
        text += f"👤 <b>{user['name']}</b> — {user['email']}\n"

    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.message(F.text == "/get")
async def get_user_start(msg: Message, state: FSMContext):
    await state.set_state(GetUser.id)
    await msg.answer("Введите ID пользователя:")


@router.message(GetUser.id)
async def get_user_by_id_handler(msg: Message, state: FSMContext):
    user = await get_user_by_id(int(msg.text))
    if user:
        await msg.answer(f"🆔 {user['id']}\n👤 {user['name']}\n📧 {user['email']}")
    else:
        await msg.answer("❌ Пользователь не найден.")
    await state.clear()


@router.message(F.text == "/update")
async def update_start(msg: Message, state: FSMContext):
    await state.set_state(UpdateUser.id)
    await msg.answer("Введите ID пользователя для обновления:")


@router.message(UpdateUser.id)
async def update_name(msg: Message, state: FSMContext):
    await state.update_data(id=int(msg.text))
    await state.set_state(UpdateUser.name)
    await msg.answer("Введите новое имя:")


@router.message(UpdateUser.name)
async def update_email(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await state.set_state(UpdateUser.email)
    await msg.answer("Введите новый email:")


@router.message(UpdateUser.email)
async def update_confirm(msg: Message, state: FSMContext):
    data = await state.get_data()
    success = await update_user_by_id(data["id"], data["name"], msg.text)
    if success:
        await msg.answer("✅ Пользователь обновлён.")
    else:
        await msg.answer("❌ Пользователь не найден.")
    await state.clear()


@router.message(F.text == "/delete")
async def delete_start(msg: Message, state: FSMContext):
    await state.set_state(DeleteUser.id)
    await msg.answer("Введите ID пользователя для удаления:")


@router.message(DeleteUser.id)
async def delete_confirm(msg: Message, state: FSMContext):
    success = await delete_user_by_id(int(msg.text))
    if success:
        await msg.answer("✅ Пользователь удалён.")
    else:
        await msg.answer("❌ Пользователь не найден.")
    await state.clear()