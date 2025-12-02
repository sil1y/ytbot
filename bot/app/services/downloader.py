import os
import uuid
import asyncio
from dataclasses import dataclass
from typing import Optional
import logging
from app.services.audio_analyzer import AudioAnalyzer
from concurrent.futures import ThreadPoolExecutor
import yt_dlp

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
        
        # ThreadPoolExecutor для CPU-bound операций (yt-dlp)
        self.executor = ThreadPoolExecutor(max_workers=2)  # 2 потока для скачиваний
        
        # Семафор для контроля асинхронных вызовов
        self.semaphore = asyncio.Semaphore(2)  # 2 одновременных скачивания

    async def download_audio(self, url: str) -> DownloadResult:
        """Асинхронное скачивание с ThreadPoolExecutor"""
        file_id = str(uuid.uuid4())
        
        async with self.semaphore:
            try:
                logger.info(f"[{file_id}] Начинаем скачивание для {url[:50]}...")
                
                # 1. Скачивание в отдельном потоке
                download_result = await self._download_in_thread(url, file_id)
                
                if not download_result.success:
                    return download_result
                
                # 2. Анализ аудио (также в отдельном потоке)
                if download_result.filename and os.path.exists(download_result.filename):
                    try:
                        loop = asyncio.get_event_loop()
                        analysis = await loop.run_in_executor(
                            self.executor,
                            self._analyze_audio_sync,
                            download_result.filename
                        )
                        
                        if analysis and analysis.get('success'):
                            download_result.audio_analysis = {
                                'bpm': analysis.get('bpm'),
                                'key': analysis.get('key')
                            }
                    except Exception as e:
                        logger.warning(f"Ошибка анализа аудио: {e}")
                
                logger.info(f"[{file_id}] Скачивание успешно завершено")
                return download_result
                
            except Exception as e:
                logger.error(f"[{file_id}] Ошибка: {e}", exc_info=True)
                return DownloadResult(success=False, error=str(e))

    async def _download_in_thread(self, url: str, file_id: str) -> DownloadResult:
        """Скачивание в отдельном потоке через ThreadPoolExecutor"""
        loop = asyncio.get_event_loop()
        
        try:
            # Запускаем скачивание в потоке из пула
            result = await loop.run_in_executor(
                self.executor,
                self._download_sync,
                url,
                file_id
            )
            return result
            
        except Exception as e:
            logger.error(f"[{file_id}] Ошибка в потоке: {e}")
            return DownloadResult(success=False, error=f"Ошибка скачивания: {str(e)}")

    def _download_sync(self, url: str, file_id: str) -> DownloadResult:
        """Синхронное скачивание (выполняется в потоке)"""
        try:
            # Уникальные настройки для каждого скачивания
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(self.download_dir, f'{file_id}.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'writethumbnail': False,  # Упрощаем - без обложки
                'embedthumbnail': False,
                'addmetadata': False,
                'quiet': True,
                'no_warnings': True,
                'cachedir': False,  # Важно! Отключаем общий кэш
                'socket_timeout': 30,
                'retries': 3,
                'ignoreerrors': False,
                'noplaylist': True,
                'extract_flat': False,
            }
            
            logger.info(f"[{file_id}] Запуск yt-dlp...")
            
            # Каждый вызов создает свой экземпляр yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            
            # Проверяем файл
            mp3_file = os.path.join(self.download_dir, f"{file_id}.mp3")
            
            if not os.path.exists(mp3_file):
                logger.error(f"[{file_id}] Файл не создан: {mp3_file}")
                return DownloadResult(success=False, error="Файл не создан")
            
            file_size = os.path.getsize(mp3_file)
            logger.info(f"[{file_id}] Файл создан: {file_size} bytes")
            
            return DownloadResult(
                success=True,
                filename=mp3_file,
                title=info.get('title', 'Без названия'),
                duration=info.get('duration', 0),
                uploader=info.get('uploader', 'Неизвестно')
            )
            
        except Exception as e:
            logger.error(f"[{file_id}] Ошибка yt-dlp: {e}")
            return DownloadResult(success=False, error=f"Ошибка: {str(e)[:100]}")

    def _analyze_audio_sync(self, file_path: str) -> Optional[dict]:
        """Синхронный анализ аудио (в потоке)"""
        try:
            # Используем синхронный вызов анализатора
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            from app.services.audio_analyzer import AudioAnalyzer
            analyzer = AudioAnalyzer()
            
            # Синхронный анализ через run_until_complete
            future = analyzer.analyze_audio(file_path)
            result = loop.run_until_complete(future)
            loop.close()
            
            return result
        except Exception as e:
            logger.warning(f"Ошибка синхронного анализа: {e}")
            return None

    async def cleanup_file(self, filename: str):
        """Асинхронная очистка файла"""
        try:
            if filename and os.path.exists(filename):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,  # Используем default executor для простых операций
                    os.remove,
                    filename
                )
                logger.info(f"Файл удален: {filename}")
        except Exception as e:
            logger.error(f"Ошибка очистки: {e}")
    