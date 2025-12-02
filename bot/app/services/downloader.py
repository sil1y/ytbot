import yt_dlp
import os
import uuid
import asyncio
from dataclasses import dataclass
from typing import Optional
import logging
from app.services.audio_analyzer import AudioAnalyzer
import subprocess
import tempfile

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

    # def _get_ydl_opts(self, file_id: str) -> dict:
    #     """Настройки скачивания"""
    #     return {
    #         'format': 'bestaudio/best',
    #         'outtmpl': os.path.join(self.download_dir, f'{file_id}.%(ext)s'),
    #         'postprocessors': [{
    #             'key': 'FFmpegExtractAudio',
    #             'preferredcodec': 'mp3',
    #             'preferredquality': '320',
    #         }],
    #         'writethumbnail': True,
    #         'embedthumbnail': True,
    #         'addmetadata': True,
    #         'quiet': True,
    #         'no_warnings': True,
    #         'cachedir': False,
    #         'socket_timeout': 30,
    #         'retries': 3,
    #     }

    async def download_audio(self, url: str) -> DownloadResult:
        """Основной метод скачивания"""
        file_id = str(uuid.uuid4())
        
        async with self.semaphore:
            try:
                # Скачивание через subprocess
                download_result = await self._download_via_subprocess(url, file_id)
                
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
                logger.error(f"Ошибка: {e}")
                return DownloadResult(success=False, error=str(e))

    async def _download_via_subprocess(self, url: str, file_id: str) -> DownloadResult:
        """Скачивание через subprocess (не блокирует event loop)"""
        try:
            # Запускаем yt-dlp как отдельный процесс
            cmd = [
                'yt-dlp',
                '--format', 'bestaudio/best',
                '--output', os.path.join(self.download_dir, f'{file_id}.%(ext)s'),
                '--postprocessor-args', 'ffmpeg:-c:a libmp3lame -q:a 2',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '320',
                '--embed-thumbnail',
                '--add-metadata',
                '--no-warnings',
                url
            ]
            
            logger.info(f"Запуск yt-dlp для {url[:50]}...")
            
            # Создаем subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.download_dir
            )
            
            # Ждем завершения
            stdout, stderr = await process.communicate()
            
            # Проверяем результат
            mp3_file = os.path.join(self.download_dir, f"{file_id}.mp3")
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')[:200]
                logger.error(f"yt-dlp ошибка: {error_msg}")
                return DownloadResult(success=False, error=f"Ошибка yt-dlp: {error_msg}")
            
            if not os.path.exists(mp3_file):
                return DownloadResult(success=False, error="MP3 файл не создан")
            
            # Получаем информацию о видео
            info = await self._get_video_info(url)
            
            return DownloadResult(
                success=True,
                filename=mp3_file,
                title=info.get('title', 'Без названия'),
                duration=info.get('duration', 0),
                uploader=info.get('uploader', 'Неизвестно')
            )
            
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}")
            return DownloadResult(success=False, error=f"Ошибка скачивания: {str(e)}")

    async def _get_video_info(self, url: str) -> dict:
        """Получение информации о видео без скачивания"""
        try:
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-warnings',
                '--skip-download',
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                import json
                try:
                    return json.loads(stdout.decode('utf-8'))
                except:
                    pass
                    
            return {}
            
        except Exception as e:
            logger.error(f"Ошибка получения информации: {e}")
            return {}

    async def cleanup_file(self, filename: str):
        """Очистка файла"""
        try:
            if filename and os.path.exists(filename):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, os.remove, filename)
                
                # Удаляем обложку если есть
                base_name = os.path.splitext(filename)[0]
                thumbnail = f"{base_name}.jpg"
                if os.path.exists(thumbnail):
                    os.remove(thumbnail)
                    
        except Exception as e:
            logger.error(f"Ошибка при удалении файла: {e}")