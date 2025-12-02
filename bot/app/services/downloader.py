import yt_dlp
import os
import uuid
import asyncio
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class DownloadResult:
    success: bool
    filename: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[int] = None
    uploader: Optional[str] = None
    error: Optional[str] = None

class AudioDownloader:
    def __init__(self, config):
        self.config = config
        self.download_dir = config.DOWNLOAD_DIR
        self._ensure_download_dir()

    def _ensure_download_dir(self):
        os.makedirs(self.download_dir, exist_ok=True)

    def _get_ydl_opts(self, file_id: str) -> dict:
        """Настройки для скачивания M4A аудио"""
        return {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': os.path.join(self.download_dir, f'{file_id}.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'writethumbnail': False,
            'embedthumbnail': False,
            'addmetadata': True,
            'quiet': True,
            'no_warnings': True,
            'cachedir': False,
            'socket_timeout': 30,
            'retries': 3,
            'ignoreerrors': 'True',
            'noplaylist': True,
            'extract_flat': False,
            'extractor_args': {
                'youtube': {
                    'skip': ['hls', 'dash']
                }
            },
            'geo_bypass': True,  
            'geo_bypass_country': 'US',
        }

    async def download_audio(self, url: str) -> DownloadResult:
        try:
            file_id = str(uuid.uuid4())
            ydl_opts = self._get_ydl_opts(file_id)
            ydl_opts['outtmpl'] = os.path.join(self.download_dir, f'{file_id}.%(ext)s')
            
            logger.info(f"Начинаем скачивание: {url}")
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._download_sync, 
                url, 
                ydl_opts
            )
            return result
            
        except Exception as e:
            logger.error(f"Ошибка в download_audio: {e}")
            return DownloadResult(success=False, error=f"Ошибка: {str(e)}")

    def _download_sync(self, url: str, ydl_opts: dict) -> DownloadResult:
        """Синхронная версия скачивания"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                logger.info("Начинаем скачивание файла...")
                ydl.download([url])
                
                original_filename = ydl.prepare_filename(info)
                
                if not os.path.exists(original_filename):
                    logger.error(f"Файл не найден: {original_filename}")
                    return DownloadResult(success=False, error="Файл не создан")
                
                return DownloadResult(
                    success=True,
                    filename=original_filename,
                    title=info.get('title', 'Unknown'),
                    duration=info.get('duration', 0),
                    uploader=info.get('uploader', 'Unknown')
                )
                
        except Exception as e:
            logger.error(f"Ошибка в _download_sync: {e}")
            return DownloadResult(success=False, error=f"Ошибка скачивания: {str(e)}")

    def cleanup_file(self, filename: str):
        """Удаляет временный файл"""
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
                logger.info(f"Файл удален: {filename}")
        except Exception as e:
            logger.error(f"Ошибка удаления файла: {e}")