import yt_dlp
import os
import uuid
import asyncio
from dataclasses import dataclass
from typing import Optional, List
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
                'preferredquality': '320',}],
            
            'writethumbnail': False,
            'embedthumbnail': False,
            'addmetadata': True,
            'quiet': True,
            'no_warnings': True,
            'cachedir': False,
            'socket_timeout': 30,
            'retries': 3,
            'ignoreerrors': False,  # ДОЛЖНО БЫТЬ False!
            'noplaylist': True,
            'extract_flat': False,
        }

    async def download_audio(self, url: str) -> DownloadResult:
        try:
            file_id = str(uuid.uuid4())
            ydl_opts = self._get_ydl_opts(file_id)
            logger.info(f"Начинаем скачивание: {url}")
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._download_sync, 
                url, 
                ydl_opts,
                file_id
            )
            
            if not result.success and ("Video unavailable" in str(result.error) or "not available" in str(result.error)):
                logger.warning("Видео недоступно. Пробуем скачать через прокси...")
                
                proxy_result = await self._download_with_proxies(url, file_id)
                if proxy_result.success:
                    logger.info("Успешно скачано через прокси")
                    return proxy_result
                
            return result
            
        except Exception as e:
            logger.error(f"Ошибка в download_audio: {e}")
            return DownloadResult(success=False, error=f"Ошибка: {str(e)}")

    def _download_sync(self, url: str, ydl_opts: dict, file_id: str) -> DownloadResult:
        """Синхронная версия скачивания"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Пробуем получить информацию о видео
                try:
                    info = ydl.extract_info(url, download=False)
                except yt_dlp.utils.DownloadError as e:
                    # Если ошибка при получении информации
                    error_msg = str(e)
                    logger.error(f"Ошибка получения информации: {error_msg}")
                    return DownloadResult(success=False, error=error_msg)
                
                # Если информация получена, пробуем скачать
                try:
                    ydl.download([url])
                except yt_dlp.utils.DownloadError as e:
                    # Если ошибка при скачивании
                    error_msg = str(e)
                    logger.error(f"Ошибка скачивания: {error_msg}")
                    return DownloadResult(success=False, error=error_msg)

                original_filename = os.path.join(self.download_dir, f"{file_id}.mp3")
                
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

    async def _download_with_proxies(self, url: str, file_id: str) -> DownloadResult:
        raw_proxies = self._load_raw_proxies()
        logger.info(f"Пробуем скачать через прокси. Доступно {len(raw_proxies)} прокси")
        
        for i, proxy in enumerate(raw_proxies[:10]):
            try:
                proxy = f'http://{proxy}'
                
                logger.info(f"Попытка #{i+1} через прокси: {proxy}")
                
                ydl_opts = self._get_ydl_opts(file_id)
                ydl_opts['proxy'] = proxy
                ydl_opts['socket_timeout'] = 45
                
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    self._download_sync, 
                    url, 
                    ydl_opts,
                    file_id
                )
                
                if result.success:
                    logger.info(f"Успешно скачано через прокси #{i+1}")
                    return result
                else:
                    logger.warning(f"Прокси #{i+1} не сработал: {result.error}")
                    
            except Exception as e:
                logger.error(f"Ошибка с прокси #{i+1}: {e}")
                continue
            
            await asyncio.sleep(1)
        
        logger.error("Все прокси не сработали")
        return DownloadResult(success=False, error="Не удалось скачать через прокси")

    def _load_raw_proxies(self) -> List[str]:
        proxy_file = 'bot/http_proxies.txt'
        proxies = []
        if os.path.exists(proxy_file):
            try:
                with open(proxy_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            proxies.append(line)
                logger.info(f"Загружено {len(proxies)} прокси из {proxy_file}")
            except Exception as e:
                logger.error(f"Ошибка загрузки прокси: {e}")
        else:
            logger.warning(f"Файл {proxy_file} не найден")
            
        return proxies

    def cleanup_file(self, filename: str):
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
                logger.info(f"Файл удален: {filename}")
        except Exception as e:
            logger.error(f"Ошибка удаления файла: {e}")