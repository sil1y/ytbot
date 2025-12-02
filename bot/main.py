import asyncio
import logging
import sys
import traceback
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage 

from dotenv import load_dotenv
from config import config
from app.handlers.start import router as start_router
from app.handlers.download import router as download_router
from app.handlers.errors import router as errors_router

# Базовая настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def handle_exception(exc_type, exc_value, exc_traceback):
    """Глобальный обработчик исключений"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.critical("Неперехваченное исключение:", 
                   exc_info=(exc_type, exc_value, exc_traceback))

# Устанавливаем глобальный обработчик
sys.excepthook = handle_exception

async def main():
    try:
        load_dotenv()
        bot = Bot(os.getenv('TOKEN_API'))  
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_routers(start_router, download_router, errors_router)

        # Обработчик исключений asyncio
        def handle_async_exception(loop, context):
            exception = context.get('exception')
            message = context.get('message', 'Ошибка asyncio')
            if exception:
                logger.error(f"Asyncio: {message}", exc_info=exception)
            else:
                logger.error(f"Asyncio: {message}")

        # Устанавливаем обработчик для asyncio
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(handle_async_exception)

        await bot.delete_webhook(drop_pending_updates=True)
        
        logger.info("Бот запускается...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except Exception as e:
        logger.critical(f"Критическая ошибка в main(): {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        traceback.print_exc()
        sys.exit(1)
# import asyncio
# import logging
# import os

# from aiogram import Bot, Dispatcher
# from aiogram.fsm.storage.memory import MemoryStorage 

# from dotenv import load_dotenv
# from config import config
# from app.handlers.start import router as start_router
# from app.handlers.download import router as download_router
# from app.handlers.errors import router as errors_router

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )
# logger = logging.getLogger(__name__)


# async def main():
#     load_dotenv()
#     bot=Bot(os.getenv('TOKEN_API'))  
#     dp = Dispatcher(storage=MemoryStorage())
#     dp.include_routers(start_router,download_router,errors_router)

#     await bot.delete_webhook(drop_pending_updates=True)
#     await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    
#     logger.info("Бот запускается...")

# if __name__ == "__main__":
#     asyncio.run(main())
    