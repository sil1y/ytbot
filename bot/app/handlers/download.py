import asyncio
from aiogram import Router, types, F
from aiogram.types import FSInputFile

from config import config
from app.services.downloader import AudioDownloader, DownloadResult
from app.services.validators import URLValidator
from app.utils.progress import DownloadProgress

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
        result = await downloader.download_audio(url)
        
        if not result.success:
            await progress_msg.edit_text(f"❌ {result.error}")
            return
        
        # Отправляем аудио как ответ на исходное сообщение
        await message.reply_audio(
            audio=FSInputFile(result.filename),
            title=result.title[:64] if result.title else "Audio",
            caption=result.title if result.title else "Аудио"
        )
        
        await progress_msg.delete()
        
    except Exception:
        await progress_msg.edit_text("❌ Ошибка скачивания")
    finally:
        if 'result' in locals() and result and result.filename:
            downloader.cleanup_file(result.filename)
