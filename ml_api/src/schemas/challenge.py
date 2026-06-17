from pydantic import BaseModel
from enum import Enum
from schemas.photo import Photo


class ChallengeType(str, Enum):
    BLINK = "BLINK"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    SMILE = "SMILE"


class ChallengeFrames(BaseModel):
    challenge_type: ChallengeType
    frames: list[Photo]