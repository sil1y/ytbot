import asyncio
from aiogram import Router, types, F
from aiogram.types import FSInputFile
import logging

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
    
    if not validator.is_youtube_url(url):
        await message.answer("❌ Это не похоже на YouTube ссылку. Отправьте корректную ссылку на YouTube видео.")
        return
    
    progress_msg = await message.reply("⏬ Скачиваю аудио...")
    
    try:
        is_valid, _, error_msg = await validator.validate_video(url, config.MAX_DURATION)
        if not is_valid:
            await progress_msg.edit_text(f"❌ {error_msg}")
            return
        
        result = await downloader.download_audio(url)

        if not result.success:
            await progress_msg.edit_text(f"❌ {result.error}")
            return
        
        caption = f"🎵 <b>{result.title}</b>"
        
        if result.duration:
            minutes = result.duration // 60
            seconds = result.duration % 60
            caption += f"\n⏳ <b>Длительность:</b> {minutes}:{seconds:02d}"
        
        if result.audio_analysis:            
            bpm = result.audio_analysis.get('bpm')
            caption += f"\n🎧 <b>BPM:</b> {bpm}"
                
            key = result.audio_analysis.get('key')
            caption += f"\n🎹 <b>Тональность:</b> {key}"
            
        else:
            logger.warning("audio_analysis is None или пустой")

        await message.reply_audio(
            audio=FSInputFile(result.filename),
            title=result.title[:64] if result.title else "Audio",
            caption=caption,
            parse_mode='HTML'
        )
        
        await progress_msg.delete()
        
    except Exception as e:
        logger.error(f"Ошибка в handle_download: {e}", exc_info=True)
        await progress_msg.edit_text("❌ Непредвиденная ошибка")
    finally:
        if 'result' in locals() and result and result.filename:
            try:
                downloader.cleanup_file(result.filename)
            except Exception as e:
                logger.error(f"Ошибка при удалении файла: {e}")