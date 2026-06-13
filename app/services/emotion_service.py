import cv2
import base64
import numpy as np
from datetime import datetime
import importlib
import inspect

# prefer the explicit module path; fall back to scanning the package for a FER-like class
try:
    from fer.fer import FER
except Exception:
    try:
        # older versions exported FER at package level
        from fer import FER as FER  # type: ignore
    except Exception:
        fer_mod = importlib.import_module("fer")
        FER = None
        for name, obj in vars(fer_mod).items():
            if inspect.isclass(obj) and "FER" in name.upper():
                FER = obj
                break
        if FER is None:
            raise ImportError(
                "FER class not found in installed 'fer' package. "
                "Either pin 'fer' to a compatible version (e.g. fer==20.0.4) "
                "or inspect the package for the correct class path."
            )

class EmotionService:
    def __init__(self):
        # example usage; keep mtcnn arg as before
        self.detector = FER(mtcnn=False)
        self.log_data = []
        self.emotion_list = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
        self.current_emotions = {emo: 0.0 for emo in self.emotion_list}

    def process_frame(self, frame_base64):
        """Decodes base64 frame and detects emotions."""
        try:
            if ',' in frame_base64:
                frame_base64 = frame_base64.split(',')[1]

            img_bytes = base64.b64decode(frame_base64)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                return False

            results = self.detector.detect_emotions(frame)
            if results:
                self._log_results(results)
            return True
        except Exception as e:
            print(f"Emotion processing error: {e}")
            return False

    def _log_results(self, results):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for res in results:
            emotions = res["emotions"]
            self.current_emotions = emotions.copy()
            self.log_data.append({"time": timestamp, **emotions})

    def get_and_reset_average(self):
        """Calculates average emotion since last reset and clears log."""
        if not self.log_data:
            return {emo: 0.0 for emo in self.emotion_list}

        averages = {}
        count = len(self.log_data)
        for emo in self.emotion_list:
            total = sum(row.get(emo, 0) for row in self.log_data)
            averages[emo] = round(total / count, 4)

        self.log_data = []  # Reset
        return averages
    
    def clear_logs(self):
        self.log_data = []