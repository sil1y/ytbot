import logging
from aiogram import Router
from aiogram.types import ErrorEvent

router = Router()
logger = logging.getLogger(__name__)

@router.error()
async def error_handler(event: ErrorEvent):
    """Глобальный обработчик ошибок"""
    logger.error(
        "Ошибка при обработке обновления:",
        exc_info=event.exception
    )
    await event.update.message.answer("❌ Произошла ошибка. Попробуйте позже.")