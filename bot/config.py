import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    DOWNLOAD_DIR: str = "downloads"
    MAX_DURATION: int = 3600
    
config = Config()