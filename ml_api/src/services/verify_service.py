import logging
from schemas.request import AnalyzeChallengeRequest, AnalyzeMatchRequest
from schemas.response import ChallengeAnalysisResponse, MatchResponse
from schemas.challenge import ChallengeType
from core.image_utils import decode_base64_image
from services import challenge_service, face_service, similarity_service

logger = logging.getLogger(__name__)


def process_challenge(request: AnalyzeChallengeRequest) -> ChallengeAnalysisResponse:
    challenge_type = request.challenge.challenge_type
    frames = request.challenge.frames

    logger.info(f"Processing challenge: {challenge_type} — {len(frames)} frames received.")

    passed, confidence, best_frame = challenge_service.verify(
        challenge_type=challenge_type,
        frames=frames
    )

    if not passed:
        logger.info(f"{challenge_type} failed — confidence={confidence}")
        return ChallengeAnalysisResponse(
            passed=False,
            confidence=confidence,
            fail_reason=f"{challenge_type.value}_NOT_DETECTED",
            best_frame=None
        )

    logger.info(f"{challenge_type} passed — confidence={confidence}")

    return ChallengeAnalysisResponse(
        passed=True,
        confidence=confidence,
        best_frame=best_frame  # only set for BLINK, None for turns
    )


def process_match(request: AnalyzeMatchRequest) -> MatchResponse:
    logger.info("Processing face match.")

    try:
        best_frame_image = decode_base64_image(request.best_frame.base64)
        id_photo_image = decode_base64_image(request.id_photo.base64)
    except ValueError as e:
        raise ValueError(f"Image decode failed: {e}")

    best_frame_face = face_service.analyze(best_frame_image)
    id_photo_face = face_service.analyze(id_photo_image)

    similarity = similarity_service.compare(id_photo_face, best_frame_face)

    # Liveness score is not from a model here —
    # it reflects how well the active challenges were performed.
    # Backend passes this from accumulated challenge confidences.
    # For now we return similarity only and let backend compute liveness.
    logger.info(f"Match complete — similarity={similarity}")

    return MatchResponse(
        similarity_score=similarity,
        liveness_score=0.0  # populated by backend from challenge confidences
    )