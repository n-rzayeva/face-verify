import os
from insightface.app import FaceAnalysis
from config import settings


class ModelRegistry:
    def __init__(self):
        self._face_analyzer = None

    def load(self):
        self._face_analyzer = FaceAnalysis(
            name=settings.face_recognition_model,
            allowed_modules=["detection", "recognition"],
            providers=["CPUExecutionProvider"]
        )
        self._face_analyzer.prepare(
            ctx_id=0,
            det_size=(settings.face_detection_size, settings.face_detection_size)
        )

    @property
    def face_analyzer(self) -> FaceAnalysis:
        if self._face_analyzer is None:
            raise RuntimeError("Models not loaded. Call load() first.")
        return self._face_analyzer


registry = ModelRegistry()