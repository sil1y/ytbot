from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📖 Помощь", callback_data="help"))
    keyboard.add(InlineKeyboardButton(text="🎵 Пример ссылки", callback_data="example"))
    
    welcome_text = """
🎵 <b>YouTube Audio Downloader Bot</b> 🎵

Привет! Я помогу тебе скачать аудио из YouTube видео в высоком качестве.

<b>Что я умею:</b>
• Скачивать аудио в формате MP3
• Сохранять метаданные и обложку
• Работать с видео до 1 часа

<b>Как использовать:</b>
Просто отправь мне ссылку на YouTube видео!
    """
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard.as_markup(),
        parse_mode='HTML'
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = """
🤖 <b>Инструкция по использованию</b>

1. <b>Найди видео на YouTube</b>
   - Открой YouTube в браузере или приложении
   - Выбери нужное видео

2. <b>Скопируй ссылку</b>
   - Нажми "Поделиться"
   - Выбери "Копировать ссылку"

3. <b>Отправь ссылку боту</b>
   - Вставь ссылку в чат
   - Отправь сообщение

4. <b>Получи аудио</b>
   - Бот обработает видео
   - Отправит готовый MP3 файл

<b>Поддерживаемые форматы ссылок:</b>
• https://www.youtube.com/watch?v=...
• https://youtu.be/...
• https://youtube.com/shorts/...

⚠️ <b>Ограничения:</b>
- Максимальная длительность: 1 час
- Только публичные видео
    """
    
    await message.answer(help_text, parse_mode='HTML')

@router.callback_query(lambda c: c.data == "help")
async def process_help_callback(callback: types.CallbackQuery):
    """Обработчик callback для кнопки помощи"""
    await cmd_help(callback.message)
    await callback.answer()

@router.callback_query(lambda c: c.data == "example")
async def process_example_callback(callback: types.CallbackQuery):
    """Обработчик callback для примера ссылки"""
    example_text = """
<b>Примеры корректных ссылок:</b>

<code>https://www.youtube.com/watch?v=dQw4w9WgXcQ</code>

<code>https://youtu.be/dQw4w9WgXcQ</code>

<code>https://youtube.com/shorts/abc123def</code>
    """
    
    await callback.message.answer(example_text, parse_mode='HTML')
    await callback.answer()
    
