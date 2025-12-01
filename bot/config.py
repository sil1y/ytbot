import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    DOWNLOAD_DIR: str = "downloads"
    MAX_DURATION: int = 3600
    
    # БЕЗ proxy настроек
    
    YDL_OPTS: dict = None
    
    def __post_init__(self):
        self.YDL_OPTS = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'writethumbnail': True,
            'embedthumbnail': True,
            'addmetadata': True,
        }

config = Config()