from pydantic import BaseModel
from schemas.photo import Photo
from schemas.challenge import ChallengeFrames


class AnalyzeChallengeRequest(BaseModel):
    challenge: ChallengeFrames


class AnalyzeMatchRequest(BaseModel):
    best_frame: Photo
    id_photo: Photo