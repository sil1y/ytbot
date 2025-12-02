import asyncio
from aiogram import Router, types, F
from aiogram.types import FSInputFile
import logging
import traceback

from config import config
from app.services.downloader import AudioDownloader
from app.services.validators import URLValidator

logger = logging.getLogger(__name__)
router = Router()
downloader = AudioDownloader(config)
validator = URLValidator()

@router.message(F.text)
async def handle_download(message: types.Message):
    url = message.text.strip()
    
    # Простая проверка
    if 'youtube.com' not in url and 'youtu.be' not in url:
        await message.answer("❌ Отправьте YouTube ссылку.")
        return
    
    progress_msg = await message.reply("⏬ Скачиваю аудио...")
    
    try:
        logger.info(f"Начинаем скачивание: {url}")
        result = await downloader.download_audio(url)
        
        logger.info(f"Результат скачивания: success={result.success}, error={result.error}")
        
        if not result.success:
            error_msg = result.error if result.error else "Неизвестная ошибка"
            await progress_msg.edit_text(f"❌ {error_msg}")
            return
        
        if not result.filename or not result.title:
            await progress_msg.edit_text("❌ Ошибка: нет данных о скачанном файле")
            return
        
        caption = f"🎵 <b>{result.title}</b>"
        
        if result.duration:
            minutes = result.duration // 60
            seconds = result.duration % 60
            caption += f"\n⏳ <b>Длительность:</b> {minutes}:{seconds:02d}"
        
        if result.uploader:
            caption += f"\n👤 <b>Автор:</b> {result.uploader}"
        
        if result.audio_analysis:
            logger.info(f"Анализ аудио: {result.audio_analysis}")
            if result.audio_analysis.get('bpm'):
                caption += f"\n🎧 <b>BPM:</b> {result.audio_analysis['bpm']}"
                
            key = result.audio_analysis.get('key')
            if key and key != "Не определено":
                caption += f"\n🎹 <b>Тональность:</b> {key}"

        logger.info(f"Отправляем аудио: {result.filename}")
        await message.reply_audio(
            audio=FSInputFile(result.filename),
            title=result.title[:64] if result.title else "Audio",
            caption=caption,
            parse_mode='HTML'
        )
        
        await progress_msg.delete()
        
    except Exception as e:
        logger.error(f"Ошибка в handle_download: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        await progress_msg.edit_text("❌ Ошибка скачивания")
    finally:
        if 'result' in locals() and result and result.filename:
            try:
                downloader.cleanup_file(result.filename)
            except Exception as e:
                logger.error(f"Ошибка при удалении файла: {e}")