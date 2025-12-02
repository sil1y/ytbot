"""
Анализатор аудио: определяет BPM и тональность.
Использует KeyFinder для определения тональности.
"""
import asyncio
import logging
from typing import Dict, Optional
import numpy as np
from app.services.key_finder import KeyFinder

logger = logging.getLogger(__name__)

class AudioAnalyzer:
    def __init__(self):
        try:
            self.key_finder = KeyFinder()
            self.has_key_finder = True
            logger.info("KeyFinder загружен")
        except ImportError as e:
            self.key_finder = None
            self.has_key_finder = False
            logger.warning(f"KeyFinder не загружен: {e}")

    async def analyze_audio(self, file_path: str) -> Dict:
        """
        Args:
            file_path: Путь к аудиофайлу
        Returns:
            Dict с ключами: bpm, key, key_confidence, error
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._analyze_sync,
                file_path
            )
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа аудио: {e}")
            return self._error_result(str(e))

    def _analyze_sync(self, file_path: str) -> Dict:
        try:
            if self.has_librosa:
                y, sr = self.librosa.load(file_path, duration=30, sr=22050)
            else:
                y, sr = None, None
            
            bpm = self._get_bpm_sync(y, sr) if self.has_librosa else None
            key_result = None
            if self.has_key_finder:
                key_result = self.key_finder.find_key(file_path, duration=45)
            
            # Формируем результат
            result = {
                'success': True,
                'bpm': bpm,
                'key': None,
                'error': None
            }
            
            if key_result and key_result['success']:
                result['key'] = key_result['key']
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка синхронного анализа: {e}")
            return self._error_result(str(e))

    def _get_bpm_sync(self, y: Optional[np.ndarray], sr: Optional[int]) -> Optional[float]:
        if y is None or sr is None:
            return None
        
        try:
            tempo, _ = self.librosa.beat.beat_track(y=y, sr=sr)
            if len(tempo) > 0:
                return round(float(tempo[0]), 1)
            return None
        except Exception as e:
            logger.warning(f"Ошибка определения BPM: {e}")
            return None

    def _error_result(self, error_msg: str) -> Dict:
        """Возвращает результат с ошибкой"""
        return {
            'success': False,
            'bpm': None,
            'key': None,
            'key_confidence': 0.0,
            'error': error_msg
        }

    def format_key_display(self, key: str, confidence: float) -> str:
        """Форматирует тональность для отображения"""
        if not key or key == "Не определено":
            return "Тональность не определена"
        
        if confidence > 0.8:
            return f"{key} (высокая точность)"
        elif confidence > 0.6:
            return key
        else:
            return f"{key} (низкая точность)"