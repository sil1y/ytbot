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

    async def download_audio(self, url: str) -> DownloadResult:
        """Основной метод скачивания"""
        file_id = str(uuid.uuid4())
        
        async with self.semaphore:
            try:
                # Скачивание через run_in_executor
                download_result = await self._download_simple(url, file_id)
                
                if not download_result.success:
                    return download_result
                
                # Анализ аудио
                if download_result.filename and os.path.exists(download_result.filename):
                    try:
                        analysis = await self.analyzer.analyze_audio(download_result.filename)
                        if analysis and analysis.get('success'):
                            download_result.audio_analysis = {
                                'bpm': analysis.get('bpm'),
                                'key': analysis.get('key')
                            }
                    except Exception as e:
                        logger.warning(f"Ошибка анализа аудио: {e}")
                
                return download_result
                
            except Exception as e:
                logger.error(f"Ошибка: {e}", exc_info=True)
                return DownloadResult(success=False, error=str(e))

    async def _download_simple(self, url: str, file_id: str) -> DownloadResult:
        """Простое скачивание через yt-dlp в отдельном потоке"""
        loop = asyncio.get_event_loop()
        
        try:
            # Запускаем в отдельном потоке
            info = await loop.run_in_executor(
                None,
                self._run_ydl_download,
                url,
                file_id
            )
            
            # Проверяем файл
            mp3_file = os.path.join(self.download_dir, f"{file_id}.mp3")
            
            if not os.path.exists(mp3_file):
                return DownloadResult(success=False, error="MP3 файл не создан")
            
            return DownloadResult(
                success=True,
                filename=mp3_file,
                title=info.get('title', 'Без названия'),
                duration=info.get('duration', 0),
                uploader=info.get('uploader', 'Неизвестно')
            )
            
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}", exc_info=True)
            return DownloadResult(success=False, error=f"Скачивание: {str(e)}")

    def _run_ydl_download(self, url: str, file_id: str) -> dict:
        """Синхронная функция для запуска в потоке"""
        try:
            # Простые настройки yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(self.download_dir, f'{file_id}.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
                'writethumbnail': False,  # Временно отключим
                'embedthumbnail': False,
                'addmetadata': False,
                'quiet': True,
                'no_warnings': True,
                'cachedir': False,
                'socket_timeout': 30,
                'retries': 3,
                'ignoreerrors': False,
            }
            
            logger.info(f"Запуск yt-dlp для {url[:50]}...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                logger.info(f"yt-dlp завершил: {info.get('title', 'N/A')[:50]}...")
                return info
                
        except Exception as e:
            logger.error(f"Ошибка в _run_ydl_download: {e}")
            raise

    async def cleanup_file(self, filename: str):
        """Очистка файла"""
        try:
            if filename and os.path.exists(filename):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, os.remove, filename)
                logger.info(f"Файл удален: {filename}")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла: {e}")import yt_dlp
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

    async def download_audio(self, url: str) -> DownloadResult:
        """Основной метод скачивания"""
        file_id = str(uuid.uuid4())
        
        async with self.semaphore:
            try:
                # Скачивание через run_in_executor
                download_result = await self._download_simple(url, file_id)
                
                if not download_result.success:
                    return download_result
                
                # Анализ аудио
                if download_result.filename and os.path.exists(download_result.filename):
                    try:
                        analysis = await self.analyzer.analyze_audio(download_result.filename)
                        if analysis and analysis.get('success'):
                            download_result.audio_analysis = {
                                'bpm': analysis.get('bpm'),
                                'key': analysis.get('key')
                            }
                    except Exception as e:
                        logger.warning(f"Ошибка анализа аудио: {e}")
                
                return download_result
                
            except Exception as e:
                logger.error(f"Ошибка: {e}", exc_info=True)
                return DownloadResult(success=False, error=str(e))

    async def _download_simple(self, url: str, file_id: str) -> DownloadResult:
        """Простое скачивание через yt-dlp в отдельном потоке"""
        loop = asyncio.get_event_loop()
        
        try:
            # Запускаем в отдельном потоке
            info = await loop.run_in_executor(
                None,
                self._run_ydl_download,
                url,
                file_id
            )
            
            # Проверяем файл
            mp3_file = os.path.join(self.download_dir, f"{file_id}.mp3")
            
            if not os.path.exists(mp3_file):
                return DownloadResult(success=False, error="MP3 файл не создан")
            
            return DownloadResult(
                success=True,
                filename=mp3_file,
                title=info.get('title', 'Без названия'),
                duration=info.get('duration', 0),
                uploader=info.get('uploader', 'Неизвестно')
            )
            
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}", exc_info=True)
            return DownloadResult(success=False, error=f"Скачивание: {str(e)}")

    def _run_ydl_download(self, url: str, file_id: str) -> dict:
        """Синхронная функция для запуска в потоке"""
        try:
            # Простые настройки yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(self.download_dir, f'{file_id}.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
                'writethumbnail': False,  # Временно отключим
                'embedthumbnail': False,
                'addmetadata': False,
                'quiet': True,
                'no_warnings': True,
                'cachedir': False,
                'socket_timeout': 30,
                'retries': 3,
                'ignoreerrors': False,
            }
            
            logger.info(f"Запуск yt-dlp для {url[:50]}...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                logger.info(f"yt-dlp завершил: {info.get('title', 'N/A')[:50]}...")
                return info
                
        except Exception as e:
            logger.error(f"Ошибка в _run_ydl_download: {e}")
            raise

    async def cleanup_file(self, filename: str):
        """Очистка файла"""
        try:
            if filename and os.path.exists(filename):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, os.remove, filename)
                logger.info(f"Файл удален: {filename}")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла: {e}")