"""
Original script from: https://github.com/Corentin-Lcs/music-key-finder
"""
import numpy as np
import librosa
import logging

logger = logging.getLogger(__name__)

class KeyFinder:
    def __init__(self):
        # Krumhansl Kessler profiles
        self.major = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        self.minor = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
        
        self.major = np.array(self.major) / np.linalg.norm(self.major)
        self.minor = np.array(self.minor) / np.linalg.norm(self.minor)
        
        self.notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.modes = ['major', 'minor']

    def find_key(self, file_path: str, duration: int = 30) -> dict:
        """
        Args:
            file_path: Path to audio file
            duration: Duration to analyze in seconds
            
        Returns:
            dict: {'key': str, 'confidence': float, 'error': str or None}
        """
        try:
            y, sr = librosa.load(file_path, duration=duration, sr=22050)
            
            key, confidence = self._compute_key(y, sr)
            
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

    def _compute_key(self, y: np.ndarray, sr: int) -> tuple:
        try:
            correlations = []
            y_harmonic, _ = librosa.effects.hpss(y)
            chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)
            chroma_norm = chroma_mean / np.linalg.norm(chroma_mean)
            
            for i in range(12): 
                chroma_shifted = np.roll(chroma_norm, -i)
                
                corr_major = np.corrcoef(chroma_shifted, self.major)[0, 1]
                correlations.append(('major', i, corr_major))
                
                corr_minor = np.corrcoef(chroma_shifted, self.minor)[0, 1]
                correlations.append(('minor', i, corr_minor))

            best_mode, best_idx, best_corr = max(correlations, key=lambda x: x[2])
            note = self.notes[best_idx]
            mode = best_mode
            confidence = min(max(best_corr, 0.0), 1.0)
            
            return f"{note} {mode}", confidence
            
        except Exception as e:
            logger.error(f"Error in key computation: {e}")
            return "Не определено", 0.0

    def format_key_for_display(self, key: str, confidence: float) -> str:
        """Format key for display with optional confidence indicator"""
        if not key or key == "Не определено":
            return "Тональность: Не определено"
        
        if confidence > 0.8:
            return f"🎹 {key} (высокая точность)"
        elif confidence > 0.6:
            return f"🎹 {key}"
        else:
            return f"🎹 {key} (низкая точность)"