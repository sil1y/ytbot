import yt_dlp
import os
import uuid
import asyncio
from dataclasses import dataclass
from typing import Optional
import logging


from pytube import YouTube
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

    def _get_ydl_opts(self) -> dict:
        """Настройки yt-dlp БЕЗ proxy"""
        base_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'writethumbnail': True,
            'embedthumbnail': True,
            'addmetadata': True,
            'socket_timeout': 120,
            'retries': 10,
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'ffprobe_location': '/usr/bin/ffprobe',
        }
        return base_opts

    async def download_audio(self, url: str) -> DownloadResult:
        """Скачивает аудио БЕЗ proxy"""
        try:
            file_id = str(uuid.uuid4())
            ydl_opts = self._get_ydl_opts()
            ydl_opts['outtmpl'] = os.path.join(self.download_dir, f'{file_id}.%(ext)s')
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._download_sync, 
                url, 
                ydl_opts
            )
            return result
            
        except Exception as e:
            return DownloadResult(success=False, error=f"Ошибка: {str(e)}")

    def _download_sync(self, url: str, ydl_opts: dict) -> DownloadResult:
        """Синхронная версия скачивания"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                mp3_filename = os.path.splitext(filename)[0] + '.mp3'
                
                if not os.path.exists(mp3_filename):
                    return DownloadResult(success=False, error="Файл не создан")
                
                return DownloadResult(
                    success=True,
                    filename=mp3_filename,
                    title=info.get('title', 'Unknown'),
                    duration=info.get('duration', 0),
                    uploader=info.get('uploader', 'Unknown')
                )
                
        except Exception as e:
            return DownloadResult(success=False, error=f"Ошибка скачивания: {str(e)}")

    def cleanup_file(self, filename: str):
        """Удаляет временный файл"""
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            logger.error(f"Ошибка удаления файла: {e}")