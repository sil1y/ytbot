import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage 

from dotenv import load_dotenv
from config import config
from app.handlers.start import router as start_router
from app.handlers.download import router as download_router
from app.handlers.errors import router as errors_router

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    load_dotenv()
    bot=Bot(os.getenv('TOKEN_API'))  
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(start_router,download_router,errors_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    
    logger.info("Бот запускается...")

if __name__ == "__main__":
    asyncio.run(main())
    