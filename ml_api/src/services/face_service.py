import logging
import numpy as np
from dataclasses import dataclass
from core.model_registry import registry
from core.image_utils import resize_for_processing

logger = logging.getLogger(__name__)


@dataclass
class FaceData:
    embedding: np.ndarray
    coverage: float
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)


def analyze(image: np.ndarray) -> FaceData:
    image = resize_for_processing(image)
    faces = registry.face_analyzer.get(image)

    if not faces:
        logger.warning("No face detected in image.")
        raise ValueError("No face detected in image.")

    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

    h, w = image.shape[:2]
    x1, y1, x2, y2 = face.bbox.astype(int)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    coverage = ((x2 - x1) * (y2 - y1)) / (h * w)

    logger.info(f"Face detected — coverage={round(coverage, 3)}")

    return FaceData(
        embedding=face.normed_embedding,
        coverage=coverage,
        bbox=(x1, y1, x2, y2)
    )