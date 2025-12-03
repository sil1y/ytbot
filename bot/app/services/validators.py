import re
import yt_dlp
import asyncio
from typing import Tuple, Optional

class URLValidator:
    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """Проверяет, является ли ссылка YouTube ссылкой"""
        youtube_patterns = [
            r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$',
            r'^https?://youtu\.be/[^/]+$'
        ]
        
        return any(re.match(pattern, url) for pattern in youtube_patterns)
    
    @staticmethod
    async def validate_video(url: str, max_duration: int = 3600) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Проверяет видео перед скачиванием
        
        Args:
            url: YouTube ссылка
            max_duration: Максимальная длительность в секундах (по умолчанию 1 час)
            
        Returns:
            Tuple[bool, dict, str]: (is_valid, video_info, error_message)
        """
        try:
            # Запускаем в отдельном потоке чтобы не блокировать event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                URLValidator._validate_video_sync, 
                url, 
                max_duration
            )
            return result
            
        except Exception as e:
            return False, None, f"Ошибка проверки видео: {str(e)}"
    
    @staticmethod
    def _validate_video_sync(url: str, max_duration: int) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Синхронная версия проверки видео"""
        try:
            # Минимальные настройки для быстрой проверки
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 15,
                'extract_flat': True,  # Быстрая проверка без скачивания
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                duration = info.get('duration', 0)
                if duration > max_duration:
                    return False, None, f"Видео слишком длинное (больше 1 часа)"
                
                # Проверяем доступность
                if info.get('availability') and info.get('availability') != 'public':
                    return False, None, "Видео недоступно для скачивания"
                
                return True, info, None
                
        except yt_dlp.utils.DownloadError as e:
            if "Private video" in str(e):
                return False, None, "Это приватное видео"
            else:
                return False, None, f"Ошибка доступа: {str(e)}"