import os
from collections import OrderedDict
from insightface.app import FaceAnalysis
import torch
from core.MiniFASNet import MiniFASNetV2
from config import settings

class ModelRegistry:
    def __init__(self):
        self._face_analyzer = None
        self._liveness_model = None

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

        liveness_model_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            settings.liveness_model_path
        )
        state_dict = torch.load(liveness_model_path, map_location="cpu", weights_only=True)
        new_state_dict = OrderedDict(
            (k.replace("module.", ""), v) for k, v in state_dict.items()
        )
        self._liveness_model = MiniFASNetV2(conv6_kernel=(5, 5))
        self._liveness_model.load_state_dict(new_state_dict)
        self._liveness_model.eval()

    @property
    def face_analyzer(self) -> FaceAnalysis:
        if self._face_analyzer is None:
            raise RuntimeError("Models not loaded. Call load() first.")
        return self._face_analyzer

    @property
    def liveness_model(self) -> MiniFASNetV2:
        if self._liveness_model is None:
            raise RuntimeError("Models not loaded. Call load() first.")
        return self._liveness_model

registry = ModelRegistry()