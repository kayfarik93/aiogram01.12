import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError
from project.middleware.admin_only import AdminOnlyMiddleware
from project.middleware.rate_limit import RateLimitMiddleware
from project.handlers import routes
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=MemoryStorage())

    # dp.message.middleware(AdminOnlyMiddleware())
    dp.message.middleware(RateLimitMiddleware(limit_seconds=1.0))

    dp.include_router(routes.router)

    await bot.set_my_commands([
        BotCommand(command="start", description="Старт работы"),
        BotCommand(command="cart", description="Корзина товаров"),
        BotCommand(command="help", description="Проблемы с ботом"),
        BotCommand(command="help_admin", description="Для администраторов")
    ])

    try:
        await dp.start_polling(bot)
    except TelegramAPIError as e:
        logging.error(f"Ошибка при запуске TelegramAPIError: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())