import asyncio
from aiogram import Router, types, F
from aiogram.types import FSInputFile
import logging
import os

from config import config
from app.services.downloader import AudioDownloader
from app.services.validators import URLValidator

logger = logging.getLogger(__name__)
router = Router()

# Простой асинхронный загрузчик
downloader = AudioDownloader(config)
validator = URLValidator()

@router.message(F.text)
async def handle_download(message: types.Message):
    url = message.text.strip()
    
    if not validator.is_youtube_url(url):
        await message.answer("❌ Это не похоже на YouTube ссылку.")
        return
    
    status_msg = await message.reply("⏬ Скачиваю аудио...")
    
    try:
        is_valid, _, error_msg = await validator.validate_video(url, config.MAX_DURATION)
        if not is_valid:
            await status_msg.edit_text(f"❌ {error_msg}")
            return
        
        logger.info(f"Начинаем скачивание: {url[:50]}...")
        
        result = await downloader.download_audio(url)

        if not result.success:
            await status_msg.edit_text(f"❌ {result.error}")
            return
        
        caption = f"🎵 <b>{result.title}</b>"
        
        if result.duration:
            minutes = result.duration // 60
            seconds = result.duration % 60
            caption += f"\n⏳ <b>Длительность:</b> {minutes}:{seconds:02d}"
        
        # if result.audio_analysis:            
        #     caption += f"\n🎧 <b>BPM:</b> {result.audio_analysis.get('bpm')}"
        #     caption += f"\n🎹 <b>Тональность:</b> {result.audio_analysis.get('key')}"
        
        await message.reply_audio(
            audio=FSInputFile(result.filename),
            title=(result.title[:64] if result.title else "Audio"),
            caption=caption,
            parse_mode='HTML'
        )
        
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        await status_msg.edit_text("❌ Ошибка при обработке")
        
    finally:
        try:
            if 'result' in locals() and result and result.filename:
                downloader.cleanup_file(result.filename)
        except Exception as e:
            logger.error(f"Ошибка при удалении файла: {e}")