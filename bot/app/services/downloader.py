import yt_dlp
import os
import uuid
import asyncio
import subprocess
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
        self.lock = asyncio.Lock()
        self._first_run = True

    def _ensure_download_dir(self):
        os.makedirs(self.download_dir, exist_ok=True)

    def _get_ydl_opts(self, file_id: str) -> dict:
        """Скачиваем аудио в формате m4a без конвертации"""
        return {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': os.path.join(self.download_dir, f'{file_id}.%(ext)s'),
            'writethumbnail': False,
            'embedthumbnail': False,
            'addmetadata': True,
            'quiet': True,
            'no_warnings': True,
            'cachedir': False,
            'socket_timeout': 30,
            'retries': 3,
            'ignoreerrors': False,
            'noplaylist': True,
            'extract_flat': False,
            'no_color': True,
            'no_call_home': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            },
        }

    async def download_audio(self, url: str) -> DownloadResult:
        """Скачивает аудио в формате m4a и конвертирует в MP3"""
        file_id = str(uuid.uuid4())
        
        async with self.lock:
            try:
                logger.info(f"Начинаем скачивание: {url}")
                
                # Запускаем синхронное скачивание
                loop = asyncio.get_event_loop()
                download_result = await loop.run_in_executor(
                    None, 
                    self._download_and_convert_sync, 
                    url, 
                    file_id
                )
                
                if self._first_run and download_result.success:
                    self._first_run = False
                    logger.info("Первый запуск yt-dlp успешен, флаг снят")
                
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
                        # Пропускаем - анализ не критичен
                
                return download_result
                
            except Exception as e:
                logger.error(f"Ошибка в download_audio: {e}", exc_info=True)
                return DownloadResult(success=False, error=f"Ошибка: {str(e)}")

    def _download_and_convert_sync(self, url: str, file_id: str) -> DownloadResult:
        """Синхронное скачивание и конвертация"""
        try:
            logger.info(f"Запуск yt-dlp для {url[:50]}...")
            
            # Скачиваем в m4a
            ydl_opts = self._get_ydl_opts(file_id)
            m4a_path = None
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Ищем скачанный файл
                m4a_path = os.path.join(self.download_dir, f"{file_id}.m4a")
                if not os.path.exists(m4a_path):
                    # Пробуем найти по другому расширению
                    for ext in ['m4a', 'webm', 'opus', 'mp4']:
                        temp_path = os.path.join(self.download_dir, f"{file_id}.{ext}")
                        if os.path.exists(temp_path):
                            m4a_path = temp_path
                            break
                
                if not os.path.exists(m4a_path):
                    return DownloadResult(success=False, error="Аудиофайл не найден после загрузки")
            
            # Конвертируем в MP3
            mp3_path = os.path.join(self.download_dir, f"{file_id}.mp3")
            self._convert_to_mp3(m4a_path, mp3_path)
            
            # Удаляем исходный m4a файл
            if os.path.exists(m4a_path):
                os.remove(m4a_path)
            
            # Проверяем результат
            if not os.path.exists(mp3_path):
                return DownloadResult(success=False, error="Не удалось конвертировать в MP3")
            
            file_size = os.path.getsize(mp3_path)
            if file_size == 0:
                os.remove(mp3_path) if os.path.exists(mp3_path) else None
                return DownloadResult(success=False, error="Файл MP3 пустой")
            
            logger.info(f"Файл создан: {mp3_path} ({file_size} bytes)")
            
            return DownloadResult(
                success=True,
                filename=mp3_path,
                title=info.get('title', 'Без названия'),
                duration=info.get('duration', 0),
                uploader=info.get('uploader', 'Неизвестно')
            )
            
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Ошибка скачивания yt-dlp: {e}")
            return DownloadResult(success=False, error=f"Ошибка загрузки: {str(e)[:100]}")
        except Exception as e:
            logger.error(f"Ошибка в _download_and_convert_sync: {e}", exc_info=True)
            return DownloadResult(success=False, error=f"Ошибка скачивания: {str(e)[:100]}")

    def _convert_to_mp3(self, input_path: str, output_path: str):
        """Конвертирует аудиофайл в MP3 с помощью ffmpeg"""
        try:
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-codec:a', 'libmp3lame',
                '-q:a', '2',  # Качество ~190kbps
                '-map_metadata', '0',
                '-id3v2_version', '3',
                '-y',  # Перезаписать если файл существует
                output_path
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            if not os.path.exists(output_path):
                raise Exception("Файл не создан после конвертации")
                
            logger.info(f"Конвертация завершена: {input_path} -> {output_path}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg ошибка: {e.stderr}")
            raise Exception(f"Ошибка конвертации: {e.stderr[:100]}")
        except Exception as e:
            logger.error(f"Ошибка конвертации: {e}")
            raise

    def cleanup_file(self, filename: str):
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
                logger.info(f"Файл удален: {filename}")
        except Exception as e:
            logger.error(f"Ошибка удаления файла: {e}")