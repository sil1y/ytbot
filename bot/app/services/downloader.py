import os
import uuid
import asyncio
import queue
import threading
from dataclasses import dataclass
from typing import Optional, Callable
import logging
from app.services.audio_analyzer import AudioAnalyzer
import yt_dlp

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

class AsyncDownloader:
    def __init__(self, config):
        self.config = config
        self.download_dir = config.DOWNLOAD_DIR
        os.makedirs(self.download_dir, exist_ok=True)
        self.analyzer = AudioAnalyzer()
        
        # Очередь для скачиваний и worker потоки
        self.download_queue = queue.Queue()
        self.workers = []
        self._start_workers(2)  # 2 рабочих потока
        
        # Для отслеживания результатов
        self.results = {}
        self.result_events = {}

    def _start_workers(self, num_workers: int):
        """Запускаем рабочие потоки"""
        for i in range(num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"DownloadWorker-{i}"
            )
            worker.start()
            self.workers.append(worker)
        logger.info(f"Запущено {num_workers} рабочих потоков")

    def _worker_loop(self):
        """Цикл рабочего потока"""
        while True:
            try:
                task_id, url, file_id = self.download_queue.get()
                if task_id is None:  # Сигнал остановки
                    break
                    
                logger.info(f"[Worker {threading.current_thread().name}] Обработка {file_id}")
                
                result = self._download_in_thread(url, file_id)
                self.results[task_id] = result
                
                # Сигнализируем что результат готов
                if task_id in self.result_events:
                    self.result_events[task_id].set()
                    
                self.download_queue.task_done()
                
            except Exception as e:
                logger.error(f"Ошибка в рабочем потоке: {e}")

    def _download_in_thread(self, url: str, file_id: str) -> DownloadResult:
        """Скачивание в рабочем потоке"""
        try:
            # Уникальные настройки для каждого скачивания
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(self.download_dir, f'{file_id}.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'writethumbnail': False,
                'embedthumbnail': False,
                'addmetadata': False,
                'quiet': True,
                'no_warnings': True,
                'cachedir': False,
                'socket_timeout': 30,
                'retries': 3,
                'ignoreerrors': False,
                'noplaylist': True,
            }
            
            # Уникальный User-Agent для каждого потока
            import yt_dlp.utils
            yt_dlp.utils.std_headers['User-Agent'] = f'yt-dlp-{threading.current_thread().name}-{file_id[:8]}'
            
            logger.info(f"[{file_id}] Запуск yt-dlp в потоке {threading.current_thread().name}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            
            # Проверяем файл
            mp3_file = os.path.join(self.download_dir, f"{file_id}.mp3")
            
            if not os.path.exists(mp3_file):
                return DownloadResult(success=False, error="Файл не создан")
            
            return DownloadResult(
                success=True,
                filename=mp3_file,
                title=info.get('title', 'Без названия'),
                duration=info.get('duration', 0),
                uploader=info.get('uploader', 'Неизвестно')
            )
            
        except Exception as e:
            logger.error(f"[{file_id}] Ошибка: {e}")
            return DownloadResult(success=False, error=str(e))

    async def download_audio(self, url: str) -> DownloadResult:
        """Асинхронное скачивание через очередь"""
        file_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        
        try:
            logger.info(f"[{task_id}] Добавление в очередь: {url[:50]}...")
            
            # Создаем event для ожидания результата
            self.result_events[task_id] = threading.Event()
            
            # Добавляем задачу в очередь
            self.download_queue.put((task_id, url, file_id))
            
            # Ждем результат с таймаутом
            loop = asyncio.get_event_loop()
            
            # Ожидаем завершения задачи
            def wait_for_result():
                return self.result_events[task_id].wait(timeout=300)  # 5 минут таймаут
            
            completed = await loop.run_in_executor(None, wait_for_result)
            
            if not completed:
                # Таймаут
                del self.result_events[task_id]
                return DownloadResult(success=False, error="Таймаут скачивания")
            
            # Получаем результат
            result = self.results.pop(task_id, None)
            del self.result_events[task_id]
            
            if not result:
                return DownloadResult(success=False, error="Результат не получен")
            
            if not result.success:
                return result
            
            # Анализ аудио
            if result.filename and os.path.exists(result.filename):
                try:
                    analysis = await self.analyzer.analyze_audio(result.filename)
                    if analysis and analysis.get('success'):
                        result.audio_analysis = {
                            'bpm': analysis.get('bpm'),
                            'key': analysis.get('key')
                        }
                except Exception as e:
                    logger.warning(f"Ошибка анализа аудио: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"[{task_id}] Ошибка: {e}")
            # Очистка
            self.result_events.pop(task_id, None)
            self.results.pop(task_id, None)
            return DownloadResult(success=False, error=str(e))

    async def cleanup_file(self, filename: str):
        """Очистка файла"""
        try:
            if filename and os.path.exists(filename):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, os.remove, filename)
        except:
            pass
    