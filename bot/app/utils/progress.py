import asyncio
from typing import Callable
from aiogram import Bot

class DownloadProgress:
    
    def __init__(self, bot: Bot, chat_id: int, message_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self.message_id = message_id
        self.last_update = 0
        
    async def update_progress(self, d: dict) -> None:
        """Обновляет сообщение с прогрессом"""
        if d['status'] == 'downloading':
            current_time = asyncio.get_event_loop().time()
            
            if current_time - self.last_update < 2:
                return
                
            self.last_update = current_time
            
            percent = d.get('_percent_str', '0%').strip()
            speed = d.get('_speed_str', 'N/A').strip()
            eta = d.get('_eta_str', 'N/A').strip()
            
            text = (
                "⏬ <b>Скачивание аудио</b>\n\n"
                f"📊 <b>Прогресс:</b> <code>{percent}</code>\n"
                f"🚀 <b>Скорость:</b> <code>{speed}</code>\n"
                f"⏱️ <b>Осталось:</b> <code>{eta}</code>"
            )
            
            try:
                await self.bot.edit_message_text(
                    chat_id=self.chat_id,
                    message_id=self.message_id,
                    text=text,
                    parse_mode='HTML'
                )
            except Exception:
                pass 
                
        elif d['status'] == 'processing':
            text = "🎵 <b>Обработка аудио</b>\n\nКонвертирую в MP3..."
            try:
                await self.bot.edit_message_text(
                    chat_id=self.chat_id,
                    message_id=self.message_id,
                    text=text,
                    parse_mode='HTML'
                )
            except Exception:
                pass