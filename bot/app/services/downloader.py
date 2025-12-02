import yt_dlp
import os
import uuid
import asyncio
from dataclasses import dataclass
from typing import Optional
import logging
import subprocess
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
        return {
            # Используем любой аудио формат
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            
            # Альтернативные варианты
            'format_sort': ['size', 'br'],
            
            # Минимальные настройки для скорости
            'quiet': True,
            'no_warnings': False,
            'socket_timeout': 15,
            'retries': 3,
            'ignoreerrors': 'only_download',
            
            # Не используем postprocessors - конвертируем сами через ffmpeg
            'writethumbnail': False,
            'embedthumbnail': False,
            'addmetadata': False,
            'consoletitle': False,
        }

    async def download_audio(self, url: str) -> DownloadResult:
        """Скачивает аудио и конвертирует в MP3 через ffmpeg"""
        try:
            file_id = str(uuid.uuid4())
            ydl_opts = self._get_ydl_opts()
            ydl_opts['outtmpl'] = os.path.join(self.download_dir, f'{file_id}.%(ext)s')
            
            logger.info(f"Начинаем скачивание: {url}")
            
            loop = asyncio.get_event_loop()
            download_result = await loop.run_in_executor(
                None, 
                self._download_and_convert, 
                url, 
                ydl_opts,
                file_id
            )
            
            if not download_result.success:
                return download_result
            
            # Анализ аудио
            audio_analysis = None
            if self.analyzer and download_result.filename:
                try:
                    analysis_result = await self.analyzer.analyze_audio(download_result.filename)
                    if analysis_result and analysis_result.get('success'):
                        audio_analysis = {
                            'bpm': analysis_result.get('bpm', 0),
                            'key': analysis_result.get('key', 'N/A'),
                            'key_confidence': analysis_result.get('key_confidence', 0)
                        }
                except Exception as e:
                    logger.warning(f"Ошибка анализа аудио: {e}")
            
            download_result.audio_analysis = audio_analysis
            return download_result
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return DownloadResult(success=False, error=f"Ошибка: {str(e)}")

    def _download_and_convert(self, url: str, ydl_opts: dict, file_id: str) -> DownloadResult:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Получаем путь к скачанному файлу
                downloaded_file = ydl.prepare_filename(info)
                
                if not os.path.exists(downloaded_file):
                    return DownloadResult(success=False, error="Файл не создан")
                
                # Конвертируем в MP3 (если еще не MP3)
                if downloaded_file.endswith('.mp3'):
                    mp3_filename = downloaded_file
                else:
                    mp3_filename = os.path.join(self.download_dir, f"{file_id}.mp3")
                    
                    # Простая конвертация через ffmpeg
                    try:
                        import subprocess
                        cmd = f'ffmpeg -i "{downloaded_file}" -codec:a libmp3lame -q:a 2 -vn -y "{mp3_filename}"'
                        subprocess.run(cmd, shell=True, check=True, timeout=30)
                        os.remove(downloaded_file)
                    except:
                        return

                return DownloadResult(
                    success=True,
                    filename=mp3_filename,
                    title=info.get('title', 'Без названия'),
                    duration=info.get('duration', 0),
                    uploader=info.get('uploader', 'Неизвестно')
                )
                
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}")
            return DownloadResult(success=False, error=f"Ошибка скачивания: {str(e)}")
        
    def cleanup_file(self, filename: str):
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
                logger.info(f"Файл удален: {filename}")
        except Exception as e:
            logger.error(f"Ошибка удаления файла: {e}")