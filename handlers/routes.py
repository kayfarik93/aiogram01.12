from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from project.forms import ProductSearch, AdminAddProduct
from project.client import get_product_by_title, get_all_products, create_order, get_product_by_id, create_product, \
    get_all_orders, get_order_by_id
from cloudipsp import Api, Checkout
import uuid
from dotenv import load_dotenv
import os

load_dotenv()

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
API_URL = os.getenv("API_URL").rstrip("/")

router = Router()

ADMIN_IDS = [ADMIN_ID]  # замените на реальные ID


# ✅ Проверка на админа
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# 📦 /admin_add — добавление товара
@router.message(F.text == "/admin_add")
async def admin_add_start(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ У вас нет доступа к этой команде.")
        return
    await state.set_state(AdminAddProduct.title)
    await msg.answer("Введите название товара:")


@router.message(AdminAddProduct.title)
async def admin_add_desc(msg: Message, state: FSMContext):
    await state.update_data(title=msg.text)
    await state.set_state(AdminAddProduct.desc)
    await msg.answer("Введите описание товара:")


@router.message(AdminAddProduct.desc)
async def admin_add_price(msg: Message, state: FSMContext):
    await state.update_data(desc=msg.text)
    await state.set_state(AdminAddProduct.price)
    await msg.answer("Введите цену товара (число):")


@router.message(AdminAddProduct.price)
async def admin_add_image(msg: Message, state: FSMContext):
    try:
        price = float(msg.text)
    except ValueError:
        await msg.answer("Введите корректную цену (например, 49.99):")
        return
    await state.update_data(price=price)
    await state.set_state(AdminAddProduct.image_url)
    await msg.answer("Укажите ссылку на изображение товара:")


@router.message(AdminAddProduct.image_url)
async def admin_add_finish(msg: Message, state: FSMContext):
    await state.update_data(image_url=msg.text)
    data = await state.get_data()

    success = await create_product({
        "title": data["title"],
        "desc": data["desc"],
        "price": data["price"],
        "image_url": data["image_url"]
    })

    if success:
        await msg.answer("✅ Товар успешно добавлен!")
    else:
        await msg.answer("❌ Произошла ошибка при добавлении товара.")

    await state.clear()


# 📜 /admin_orders — просмотр заказов
@router.message(F.text == "/admin_orders")
async def list_all_orders(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ У вас нет доступа.")
        return
    orders = await get_all_orders()
    if not orders:
        await msg.answer("Пока нет заказов.")
        return

    text = "<b>Все заказы:</b>\n\n"
    for order in orders:
        text += f"🛒 Order ID: {order['id']} | User ID: {order['user_id']} | Status: {order['status']} | Items: {len(order['items'])}\n"

    await msg.answer(text)


# 🔍 /admin_order <id> — просмотр заказа по ID
@router.message(F.text.startswith("/admin_order "))
async def order_details(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ У вас нет доступа.")
        return

    try:
        order_id = int(msg.text.split()[1])
    except:
        await msg.answer("❗ Используйте формат: /admin_order <id>")
        return

    order = await get_order_by_id(order_id)
    if not order:
        await msg.answer("❌ Заказ не найден.")
        return

    text = f"<b>Заказ #{order['id']}</b>\n"
    text += f"👤 Пользователь: <a href='tg://user?id={order['user_id']}'>Написать</a> (ID: {order['user_id']})\n"
    text += f"📦 Статус: {order['status']}\n\n"

    for item in order["items"]:
        text += f"- {item['product']['title']} x {item['quantity']}\n"

    await msg.answer(text, parse_mode="HTML")


@router.message(F.text.in_({"/start", "меню"}))
async def welcome_message(msg: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найти товар по названию", callback_data="search_by_title")],
            [InlineKeyboardButton(text="📦 Каталог товаров", callback_data="show_catalog:0")]
        ]
    )
    await msg.answer("Добро пожаловать! Выберите, что хотите сделать:", reply_markup=keyboard)


@router.callback_query(F.data == "search_by_title")
async def ask_for_title(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProductSearch.title)
    await callback.message.answer("Введите название товара:")
    await callback.answer()


@router.message(ProductSearch.title)
async def process_title_search(msg: Message, state: FSMContext):
    title = msg.text.strip()
    products = await get_product_by_title(title)

    if not products:
        await msg.answer("❌ Товар не найден.")
    else:
        for product in products:
            text = (
                f"<b>{product['title']}</b>\n\n"
                f"{product['desc']}\n\n"
                f"<i>Цена:</i> <b>{product['price']} $</b>"
            )
            btns = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy:{product['id']}")]
            ])
            await msg.answer_photo(
                photo=product['image_url'],
                caption=text,
                parse_mode="HTML",
                reply_markup=btns
            )

    await state.clear()


@router.callback_query(F.data.startswith("show_catalog"))
async def show_catalog(callback: CallbackQuery):
    products = await get_all_products()
    if not products:
        await callback.message.answer("❌ Каталог пуст.")
        await callback.answer()
        return

    # Индекс из callback_data: show_catalog:{index}
    index = int(callback.data.split(":")[1])
    product = products[index]

    text = (
        f"<b>{product['title']}</b>\n\n"
        f"{product['desc']}\n\n"
        f"<i>Цена:</i> <b>{product['price']} $</b>"
    )

    buttons = []
    if index > 0:
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"show_catalog:{index - 1}"))
    if index < len(products) - 1:
        buttons.append(InlineKeyboardButton(text="▶️ Вперёд", callback_data=f"show_catalog:{index + 1}"))

    pagination = InlineKeyboardMarkup(inline_keyboard=[
        buttons,
        [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy:{product['id']}")]
    ])

    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=product['image_url'],
            caption=text,
            parse_mode="HTML"
        ),
        reply_markup=pagination
    )
    await callback.answer()


# Добавление товара в корзину
@router.callback_query(F.data.startswith("buy:"))
async def buy_handler(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])

    # Получаем текущую корзину из FSM-хранилища
    data = await state.get_data()
    cart = data.get("cart", [])

    # Проверяем, есть ли уже такой товар
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += 1
            break
    else:
        cart.append({"product_id": product_id, "quantity": 1})

    await state.update_data(cart=cart)

    await callback.answer("✅ Товар добавлен в корзину")


# Просмотр корзины
@router.message(F.text == "/cart")
async def view_cart(msg: Message, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])

    if not cart:
        await msg.answer("🛒 Ваша корзина пуста.")
        return

    buttons = []
    text = "<b>🛒 Ваша корзина:</b>\n\n"
    for idx, item in enumerate(cart, start=1):
        title = await get_product_by_id(item['product_id'])
        buttons.append([InlineKeyboardButton(text=f"❌ Удалить «{title['title']}»",
                                             callback_data=f"remove_item:{item['product_id']}")])
        text += f"{idx}. Товар «{title['title']}» — Кол-во: {item['quantity']}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                                        [
                                                            InlineKeyboardButton(text="✅ Оформить заказ",
                                                                                 callback_data="confirm_order"),
                                                            InlineKeyboardButton(text="🗑 Очистить",
                                                                                 callback_data="clear_cart")
                                                        ]
                                                    ] + buttons)

    await msg.answer(text, reply_markup=keyboard)


# Очистка корзины
@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery, state: FSMContext):
    await state.update_data(cart=[])
    await callback.message.edit_text("🧹 Корзина очищена.")
    await callback.answer()


# Удаление одного товара
@router.callback_query(F.data.startswith("remove_item:"))
async def remove_item(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    cart = data.get("cart", [])
    cart = [item for item in cart if item["product_id"] != product_id]
    await state.update_data(cart=cart)
    await callback.message.edit_text(
        "❌ Товар удалён из корзины. Напиши <b>корзина</b>, чтобы посмотреть обновлённый список.")
    await callback.answer()


# Подтверждение заказа
@router.callback_query(F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])

    if not cart:
        await callback.message.answer("❗ Ваша корзина пуста.")
        return

    # Отправляем заказ в FastAPI
    result = await create_order(callback.from_user.id, cart)

    if result:
        total_cents = 0
        all_products = await get_all_products()
        for item in cart:
            for p in all_products:
                if item['product_id'] == p['id']:
                    total_cents += int(p['price']) * 100 * item['quantity']

        api = Api(merchant_id=1396424, secret_key='test')
        checkout = Checkout(api=api)
        data = {
            "currency": "USD",
            "amount": total_cents,
            "order_id": f"order_{result}_{uuid.uuid4().hex[:6]}",
            "order_desc": "Оплата заказа в Telegram",
            "server_callback_url": f"{API_URL}/webhook/fondy"
        }
        url = checkout.url(data).get("checkout_url")

        # Кнопка на оплату
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить заказ", url=url)]
        ])

        await callback.message.answer("✅ Ваш заказ оформлен!\nПерейдите по кнопке для оплаты:", reply_markup=markup)

        import asyncio
        await asyncio.sleep(3)

        # 📩 Отправляем напоминание
        await callback.message.answer("💬 После успешной оплаты с вами свяжется наш менеджер.")
        await state.update_data(cart=[])  # Очистить корзину
    else:
        await callback.message.answer("❌ Ошибка при оформлении заказа. Попробуйте позже.")

    await callback.answer()

@router.message(F.text.in_({"/help_admin"}))
async def show_help_admin(message: Message):
    await message.answer(f"/admin_add — добавление товара\n/admin_orders — просмотр заказов\n/admin_order  — просмотр заказа по ID")

@router.message(F.text.in_({"/help"}))
async def show_help(message: Message):
    await message.answer(f"Если вы нашли какие-то ошибки, недоработки в боте, у вас есть предложения и пожелания, пожалуйста, свяжитесь со мной: @kay1arik")