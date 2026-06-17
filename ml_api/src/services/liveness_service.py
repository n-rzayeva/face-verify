import logging
from dataclasses import dataclass
import numpy as np
import cv2
import torch
from core.model_registry import registry
from services.face_service import FaceData
from config import settings

logger = logging.getLogger(__name__)

_CLASS_NAMES = {0: "SPOOF", 1: "UNKNOWN", 2: "REAL"}


@dataclass
class LivenessResult:
    score: float   # confidence in the predicted label
    label: str     # "SPOOF", "UNKNOWN", or "REAL"


def score(image: np.ndarray, face_data: FaceData) -> LivenessResult:
    """
    Passive liveness check using MiniFASNetV2.

    The model outputs 3 classes (spoof, unknown, real). Rather than applying
    an additional manual threshold on top of the model's output, we trust
    the model's own classification decision (argmax) and report the
    confidence in that decision.
    """
    try:
        x1, y1, x2, y2 = face_data.bbox
        face_crop = image[y1:y2, x1:x2]
        if face_crop.size == 0:
            return LivenessResult(score=0.0, label="SPOOF")

        face_resized = cv2.resize(face_crop, (80, 80))
        face_rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)

        mean = np.array(settings.liveness_mean)
        std = np.array(settings.liveness_std)
        face_normalized = (face_rgb / 255.0 - mean) / std

        face_tensor = torch.from_numpy(face_normalized).float()
        face_tensor = face_tensor.permute(2, 0, 1).unsqueeze(0)

        with torch.no_grad():
            output = registry.liveness_model(face_tensor)
            probabilities = torch.softmax(output, dim=1)
            label_idx = int(torch.argmax(probabilities, dim=1).item())
            confidence = float(probabilities[0][label_idx])

        label = _CLASS_NAMES[label_idx]
        logger.info(f"Liveness check — label={label} confidence={round(confidence, 4)}")

        return LivenessResult(score=round(confidence, 4), label=label)

    except Exception as e:
        logger.warning(f"Liveness scoring failed: {e}")
        return LivenessResult(score=0.0, label="SPOOF")