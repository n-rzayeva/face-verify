import numpy as np
from services.face_service import FaceData


def compare(main: FaceData, comparison: FaceData) -> float:
    # Cosine similarity between two ArcFace embeddings.
    # Since embeddings are already L2 normalized, dot product = cosine similarity.
    # Raw range is -1 to 1, normalized to 0.0 - 1.0.
    similarity = float(np.dot(main.embedding, comparison.embedding))
    return round(max(0.0, min(1.0, (similarity + 1) / 2)), 4)