import re
import yt_dlp
from typing import Tuple, Optional

class URLValidator:    
    @staticmethod
    def is_youtube_url(url: str) -> bool:
        youtube_patterns = [
            r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$',
            r'^https?://youtu\.be/[^/]+$'
        ]
        
        return any(re.match(pattern, url) for pattern in youtube_patterns)
    
    @staticmethod
    async def validate_video(url: str, max_duration: int) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Returns:
            Tuple[bool, dict, str]: (is_valid, video_info, error_message)
        """
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                duration = info.get('duration', 0)
                
                if duration > max_duration:
                    return False, None, f"Видео слишком длинное (больше {max_duration//60} минут)"
                
                if info.get('availability') != 'public':
                    return False, None, "Видео недоступно для скачивания"
                
                return True, info, None
                
        except Exception as e:
            return False, None, f"Ошибка проверки видео: {str(e)}"