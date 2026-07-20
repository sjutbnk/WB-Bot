import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from config.settings import settings
from database.base import init_db
from database.requests import init_default_records
from handlers import shared
from handlers.supply_handlers import menu

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Запуск Бота планирования поставок...")
    
    # Шаг 1: Инициализация БД
    try:
        await init_db()
        await init_default_records()
        logger.info("База данных успешно инициализирована.")
    except Exception as e:
        logger.error(f"Критическая ошибка инициализации БД: {e}")
        sys.exit(1)

    # Шаг 2: Инициализация бота и диспетчера
    bot = Bot(
        token=settings.bot_token_supply,
        default=DefaultBotProperties(parse_mode="Markdown")
    )
    dp = Dispatcher()

    # Шаг 3: Регистрация роутеров
    dp.include_router(shared.router)
    dp.include_router(menu.router)

    # Шаг 4: Запуск поллинга
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
