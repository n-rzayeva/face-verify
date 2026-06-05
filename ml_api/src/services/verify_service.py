import logging
from schemas.request import AnalyzeChallengeRequest, AnalyzeMatchRequest
from schemas.response import ChallengeAnalysisResponse, MatchResponse
from core.image_utils import decode_base64_image
from services import challenge_service, face_service, similarity_service, liveness_service

logger = logging.getLogger(__name__)


def process_challenge(request: AnalyzeChallengeRequest) -> ChallengeAnalysisResponse:
    challenge_type = request.challenge.challenge_type
    frames = request.challenge.frames

    logger.info(f"Processing challenge: {challenge_type} — {len(frames)} frames received.")

    passed, confidence, best_frame, fail_reasons = challenge_service.verify(
        challenge_type=challenge_type,
        frames=frames
    )

    if not passed:
        logger.info(f"{challenge_type} failed — reasons={fail_reasons}, confidence={confidence}")
        return ChallengeAnalysisResponse(
            passed=False,
            confidence=confidence,
            fail_reasons=fail_reasons,
            best_frame=None
        )

    logger.info(f"{challenge_type} passed — confidence={confidence}")
    return ChallengeAnalysisResponse(
        passed=True,
        confidence=confidence,
        fail_reasons=[],
        best_frame=best_frame
    )


def process_match(request: AnalyzeMatchRequest) -> MatchResponse:
    logger.info("Processing face match.")

    best_frame_image = decode_base64_image(request.best_frame.base64)
    id_photo_image = decode_base64_image(request.id_photo.base64)

    best_frame_face = face_service.analyze(best_frame_image)
    id_photo_face = face_service.analyze(id_photo_image)

    similarity = similarity_service.compare(id_photo_face, best_frame_face)
    liveness = liveness_service.score(best_frame_image, best_frame_face)

    logger.info(f"Match complete — similarity={similarity} liveness={liveness}")

    return MatchResponse(
        similarity_score=similarity,
        liveness_score=liveness
    )