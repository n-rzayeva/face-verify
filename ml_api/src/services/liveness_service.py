import logging
import numpy as np
import cv2
import torch
from core.model_registry import registry
from services.face_service import FaceData
from config import settings

logger = logging.getLogger(__name__)


def score(image: np.ndarray, face_data: FaceData) -> float:
    """
    Passive liveness score using MiniFASNetV2.
    Returns probability that the face is real (class index 2).
    Range: 0.0 - 1.0
    """
    try:
        x1, y1, x2, y2 = face_data.bbox
        face_crop = image[y1:y2, x1:x2]
        if face_crop.size == 0:
            return 0.0

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
            liveness_prob = float(probabilities[0][2])  # index 2 = real class

        return round(liveness_prob, 4)

    except Exception as e:
        logger.warning(f"Liveness scoring failed: {e}")
        return 0.0