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

    def _ensure_download_dir(self):
        os.makedirs(self.download_dir, exist_ok=True)

    def _get_ydl_opts(self) -> dict:
        """Настройки для скачивания M4A аудио"""
        base_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio',
            
            # Отключение всего что требует ffmpeg
            'writethumbnail': False,
            'embedthumbnail': False,
            'addmetadata': False,
            
            'socket_timeout': 120,
            'retries': 10,
            'ignoreerrors': False,
        }
        return base_opts

    async def download_audio(self, url: str) -> DownloadResult:
        """Скачивает аудио в M4A и переименовывает в MP3"""
        try:
            file_id = str(uuid.uuid4())
            ydl_opts = self._get_ydl_opts()
            ydl_opts['outtmpl'] = os.path.join(self.download_dir, f'{file_id}.%(ext)s')
            
            logger.info(f"Начинаем скачивание: {url}")
            
            loop = asyncio.get_event_loop()
            download_result = await loop.run_in_executor(
                None, 
                self._download_sync, 
                url, 
                ydl_opts
            )
            if not download_result.success:
                return download_result
            
            audio_analysis = None
            if self.analyzer:
                try:
                    analysis_result = await self.analyzer.analyze_audio(download_result.filename)
                    if analysis_result['success']:
                        audio_analysis = {
                            'bpm': analysis_result['bpm'],
                            'key': analysis_result['key'],
                            'key_confidence': analysis_result['key_confidence']
                        }
                except Exception as e:
                    logger.warning(f"Ошибка анализа: {e}")
                    
            download_result.audio_analysis = audio_analysis
            return download_result
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return DownloadResult(success=False, error=f"Ошибка: {str(e)}")

    def _download_file(self, url: str, ydl_opts: dict) -> DownloadResult:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                if not os.path.exists(filename):
                    return DownloadResult(success=False, error="Файл не создан")
                
                # Переименовываем в MP3
                mp3_filename = os.path.splitext(filename)[0] + '.mp3'
                os.rename(filename, mp3_filename)
                
                return DownloadResult(
                    success=True,
                    filename=mp3_filename,
                    title=info.get('title', 'Unknown'),
                    duration=info.get('duration', 0),
                    uploader=info.get('uploader', 'Unknown')
                )
                
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}")
            return DownloadResult(success=False, error=f"Ошибка скачивания: {str(e)}")
        
    def cleanup_file(self, filename: str):
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            logger.error(f"Ошибка удаления файла: {e}")