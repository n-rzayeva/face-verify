from pydantic import BaseModel
from typing import Optional
from schemas.photo import Photo

class ChallengeAnalysisResponse(BaseModel):
    passed: bool
    confidence: float
    fail_reasons: list[str] = []
    best_frame: Optional[Photo] = None  # only returned for BLINK challenge


class MatchResponse(BaseModel):
    similarity_score: float
    liveness_score: float        # confidence in the predicted label
    liveness_label: str          # "SPOOF", "UNKNOWN", or "REAL"