"""
Improved key detection algorithm based on Krumhansl-Kessler profiles
"""
import numpy as np
import librosa
import logging

logger = logging.getLogger(__name__)

class KeyFinder:
    def __init__(self):
        # Krumhansl-Kessler key profiles (оригинальные значения)
        self.major = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        self.minor = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
        
        # Нормализация профилей
        self.major = np.array(self.major)
        self.minor = np.array(self.minor)
        
        # NOTES: ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.modes = ['major', 'minor']

    def find_key(self, file_path: str, duration: int = 30, start_time: float = 0.0) -> dict:
        """
        Args:
            file_path: Path to audio file
            duration: Duration to analyze in seconds
            start_time: Start time for analysis (skip beginning)
            
        Returns:
            dict: {'key': str, 'confidence': float, 'error': str or None}
        """
        try:
            # Загружаем с возможностью начать не с начала
            y, sr = librosa.load(file_path, duration=duration, sr=22050, offset=start_time)
            
            key, confidence = self._compute_key_improved(y, sr)
            
            return {
                'success': True,
                'key': key,
                'confidence': confidence,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Key detection error: {e}")
            return {
                'success': False,
                'key': None,
                'confidence': 0.0,
                'error': str(e)
            }

    def _compute_key_improved(self, y: np.ndarray, sr: int) -> tuple:
        """
        Улучшенный алгоритм определения тональности
        """
        try:
            # 1. Предварительная обработка
            # Удаляем тишину в начале/конце
            y_trimmed, _ = librosa.effects.trim(y, top_db=20)
            
            # 2. Извлечение гармонической составляющей
            y_harmonic = librosa.effects.harmonic(y_trimmed, margin=8)
            
            # 3. Вычисление хроматических признаков
            # Используем CQT для лучшего разрешения низких частот
            chroma = librosa.feature.chroma_cqt(
                y=y_harmonic, 
                sr=sr,
                n_chroma=12,
                n_octaves=7,
                bins_per_octave=36
            )
            
            # 4. Усреднение по времени с весами (учитываем громкость)
            rms = librosa.feature.rms(y=y_harmonic)[0]
            rms_normalized = rms / np.max(rms) if np.max(rms) > 0 else rms
            
            # Взвешенное усреднение
            if len(rms_normalized) == chroma.shape[1]:
                chroma_weighted = np.sum(chroma * rms_normalized, axis=1) / np.sum(rms_normalized)
            else:
                chroma_weighted = np.mean(chroma, axis=1)
            
            # Нормализация
            chroma_norm = chroma_weighted / (np.linalg.norm(chroma_weighted) + 1e-10)
            
            # 5. Корреляция с профилями Krumhansl-Kessler
            correlations = []
            
            for i in range(12):
                # Сдвигаем хроматический вектор
                chroma_shifted = np.roll(chroma_norm, -i)
                
                # Корреляция с мажорным профилем
                corr_major = self._correlation(chroma_shifted, self.major)
                correlations.append(('major', i, corr_major))
                
                # Корреляция с минорным профилем
                corr_minor = self._correlation(chroma_shifted, self.minor)
                correlations.append(('minor', i, corr_minor))
            
            # 6. Находим наилучшее соответствие
            correlations.sort(key=lambda x: x[2], reverse=True)
            
            best_mode, best_idx, best_corr = correlations[0]
            second_best = correlations[1][2] if len(correlations) > 1 else 0
            
            # 7. Вычисляем уверенность
            note = self.notes[best_idx]
            
            # Уверенность на основе разницы с вторым лучшим результатом
            if second_best > 0:
                confidence = min(max((best_corr - second_best) / (1 - second_best + 1e-10), 0.0), 1.0)
            else:
                confidence = min(max(best_corr, 0.0), 1.0)
            
            # 8. Дополнительная проверка по относительному мажору/минору
            if best_mode == 'minor':
                # Проверяем, не является ли это относительным мажором
                relative_major_idx = (best_idx + 3) % 12
                for mode, idx, corr in correlations:
                    if mode == 'major' and idx == relative_major_idx and abs(corr - best_corr) < 0.1:
                        # Возможно, это относительная пара
                        if corr > best_corr * 0.95:
                            # Если разница менее 5%, выбираем мажор (более уверенно)
                            best_mode = 'major'
                            best_idx = relative_major_idx
                            note = self.notes[relative_major_idx]
                            break
            
            return f"{note} {best_mode}", round(confidence, 3)
            
        except Exception as e:
            logger.error(f"Error in key computation: {e}")
            return "Не определено", 0.0
    
    def _correlation(self, a: np.ndarray, b: np.ndarray) -> float:
        """Вычисляет корреляцию Пирсона"""
        a_norm = a - np.mean(a)
        b_norm = b - np.mean(b)
        
        numerator = np.sum(a_norm * b_norm)
        denominator = np.sqrt(np.sum(a_norm ** 2) * np.sum(b_norm ** 2))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def find_key_multi_segment(self, file_path: str, segments: int = 3) -> dict:
        """
        Анализ нескольких сегментов для большей точности
        """
        try:
            y, sr = librosa.load(file_path, sr=22050)
            duration = librosa.get_duration(y=y, sr=sr)
            
            if duration < 10:  # Слишком короткий трек
                return self.find_key(file_path)
            
            segment_duration = min(30, duration / segments)
            results = []
            
            for i in range(segments):
                start = i * (duration - segment_duration) / max(segments - 1, 1)
                result = self.find_key(file_path, duration=segment_duration, start_time=start)
                if result['success']:
                    results.append(result['key'])
            
            # Выбираем наиболее частую тональность
            if results:
                from collections import Counter
                most_common = Counter(results).most_common(1)[0]
                return {
                    'success': True,
                    'key': most_common[0],
                    'confidence': most_common[1] / len(results),
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'key': None,
                    'confidence': 0.0,
                    'error': "Не удалось определить тональность"
                }
                
        except Exception as e:
            logger.error(f"Multi-segment error: {e}")
            return self.find_key(file_path)