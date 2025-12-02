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

class AudioDownloader:
    def __init__(self, config):
        self.config = config
        self.download_dir = config.DOWNLOAD_DIR
        self._ensure_download_dir()
        self.analyzer = AudioAnalyzer()
        # Блокировка для одного скачивания за раз
        self.lock = asyncio.Lock()

    def _ensure_download_dir(self):
        os.makedirs(self.download_dir, exist_ok=True)

    def _get_ydl_opts(self) -> dict:
        """Настройки для скачивания с автоматической конвертацией в MP3"""
        return {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.download_dir, '%(id)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'writethumbnail': False,
            'embedthumbnail': False,
            'addmetadata': False,
            'quiet': True,
            'no_warnings': True,
            'cachedir': False,
            'socket_timeout': 30,
            'retries': 3,
            'ignoreerrors': False,
            'noplaylist': True,
        }

    async def download_audio(self, url: str) -> DownloadResult:
        """Скачивает аудио и конвертирует в MP3"""
        file_id = str(uuid.uuid4())
        
        # Только одно скачивание одновременно
        async with self.lock:
            try:
                ydl_opts = self._get_ydl_opts()
                ydl_opts['outtmpl'] = os.path.join(self.download_dir, f'{file_id}.%(ext)s')
                
                logger.info(f"Начинаем скачивание: {url}")
                
                loop = asyncio.get_event_loop()
                download_result = await loop.run_in_executor(
                    None, 
                    self._download_sync, 
                    url, 
                    ydl_opts,
                    file_id
                )
                
                if not download_result.success:
                    return download_result
                
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
                logger.error(f"Ошибка в download_audio: {e}")
                return DownloadResult(success=False, error=f"Ошибка: {str(e)}")

    def _download_sync(self, url: str, ydl_opts: dict, file_id: str) -> DownloadResult:
        try:
            logger.info(f"Запуск yt-dlp для {url[:50]}...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                logger.info(f"Информация получена: {info.get('title', 'N/A')[:50]}...")
                
                # Скачиваем
                ydl.download([url])
                
                # Проверяем созданный MP3 файл
                mp3_filename = os.path.join(self.download_dir, f"{file_id}.mp3")
                
                if not os.path.exists(mp3_filename):
                    logger.error(f"MP3 файл не создан: {mp3_filename}")
                    return DownloadResult(success=False, error="Файл не создан")
                
                return DownloadResult(
                    success=True,
                    filename=mp3_filename,
                    title=info.get('title', 'Без названия'),
                    duration=info.get('duration', 0),
                    uploader=info.get('uploader', 'Неизвестно')
                )
                
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Ошибка скачивания yt-dlp: {e}")
            return DownloadResult(success=False, error=f"Ошибка YouTube: {str(e)[:100]}")
        except Exception as e:
            logger.error(f"Ошибка в _download_sync: {e}")
            return DownloadResult(success=False, error=f"Ошибка скачивания: {str(e)[:100]}")

    def cleanup_file(self, filename: str):
        """Удаляет временный файл"""
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
                logger.info(f"Файл удален: {filename}")
        except Exception as e:
            logger.error(f"Ошибка удаления файла: {e}")