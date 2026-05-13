from dataclasses import dataclass
import numpy as np


@dataclass
class FaceData:
    embedding: np.ndarray
    coverage: float
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)