import yt_dlp
import os
import uuid
import asyncio
from dataclasses import dataclass
from typing import Optional
import logging
from app.services.audio_analyzer import AudioAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class DownloadResult:
    success: bool
    filename: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[int] = None
    audio_analysis: Optional[dict] = None
    uploader: Optional[str] = None
    error: Optional[str] = None

class AsyncDownloader:
    def __init__(self, config):
        self.config = config
        self.download_dir = config.DOWNLOAD_DIR
        os.makedirs(self.download_dir, exist_ok=True)
        self.analyzer = AudioAnalyzer()
        self.semaphore = asyncio.Semaphore(5) 

    def _get_ydl_opts(self, file_id: str) -> dict:
        """Настройки скачивания"""
        return {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.download_dir, f'{file_id}.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'writethumbnail': True,
            'embedthumbnail': True,
            'addmetadata': True,
            'quiet': True,
            'no_warnings': True,
            'cachedir': False,
        }

    async def download_audio(self, url: str) -> DownloadResult:
        """Основной метод скачивания с защитой от перегрузки"""
        file_id = str(uuid.uuid4())
        
        async with self.semaphore:
            try:
                download_result = await self._download(url, file_id)
                if not download_result.success:
                    return download_result
                
                if download_result.filename:
                    analysis = await self.analyzer.analyze_audio(download_result.filename)
                    download_result.audio_analysis = {
                        'bpm': analysis.get('bpm'),
                        'key': analysis.get('key')}
                
                return download_result
                
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                return DownloadResult(success=False, error=str(e))

    async def _download(self, url: str, file_id: str) -> DownloadResult:
        ydl_opts = self._get_ydl_opts(file_id)
        
        loop = asyncio.get_event_loop() 
        try:
            info = await loop.run_in_executor(
                None,
                self._run_ydl,
                url,
                ydl_opts
            )
            
            mp3_file = os.path.join(self.download_dir, f"{file_id}.mp3")
            if not os.path.exists(mp3_file):
                return DownloadResult(success=False, error="Файл не создан")
            
            return DownloadResult(
                success=True,
                filename=mp3_file,
                title=info.get('title', 'Без названия'),
                duration=info.get('duration', 0),
                uploader=info.get('uploader', 'Неизвестно')
            )
            
        except Exception as e:
            return DownloadResult(success=False, error=f"Скачивание: {str(e)}")

    def _run_ydl(self, url: str, ydl_opts: dict) -> dict:
        """Запуск yt-dlp"""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    async def cleanup_file(self, filename: str):
        """Очистка файла"""
        try:
            if filename and os.path.exists(filename):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, os.remove, filename)
        except:
            pass