import logging
import cv2
import numpy as np
from config import settings
from core.landmark_extractor import extractor
from schemas.request import AnalyzeChallengeRequest, AnalyzeMatchRequest
from schemas.response import ChallengeAnalysisResponse, MatchResponse
from schemas.challenge import ChallengeType
from core.image_utils import decode_base64_image
from services import challenge_service, face_service, similarity_service
from services.face_service import FaceData

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


def _compute_liveness(
    image: np.ndarray,
    face_data: FaceData,
    challenge_confidences: dict[str, float]
) -> float:
    """
    Liveness score combining:
      1. Challenge confidence scores — did active challenges happen genuinely?
         Higher weight — this is the core liveness signal.
      2. Best frame quality signals — is the captured frame usable?
         Lower weight — supporting signal.

    Neither alone is sufficient:
      - Challenge confidence without quality = might have passed with bad frames
      - Quality without challenge confidence = passive only, spoofable
    """

    # --- Challenge confidence score (active liveness signal) ---
    if challenge_confidences:
        challenge_score = sum(challenge_confidences.values()) / len(challenge_confidences)
    else:
        challenge_score = 0.0

    # --- Frame quality signals (passive supporting signal) ---

    # Blur
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    blur_score = min(blur / settings.blur_threshold, 1.0)

    # Brightness
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    brightness = float(hsv[:, :, 2].mean())
    if brightness < settings.min_brightness:
        brightness_score = brightness / settings.min_brightness
    elif brightness > settings.max_brightness:
        brightness_score = settings.max_brightness / brightness
    else:
        brightness_score = 1.0

    # Face coverage
    coverage_score = min(face_data.coverage / settings.min_face_coverage, 1.0)

    # Landmark quality
    landmarks = extractor.extract(image)
    if landmarks is not None:
        eyes_score = 1.0 if landmarks.eyes_open else 0.5
        frontal_score = 1.0 if landmarks.is_frontal else 0.7
    else:
        eyes_score = 0.5
        frontal_score = 0.5

    # Quality score = average of frame quality signals
    quality_score = (
        blur_score * 0.35 +
        brightness_score * 0.25 +
        coverage_score * 0.20 +
        eyes_score * 0.10 +
        frontal_score * 0.10
    )

    # Final liveness:
    # Challenge confidence carries more weight — it's the active proof
    # Quality is a supporting signal
    liveness = (challenge_score * 0.65) + (quality_score * 0.35)

    return round(liveness, 4)


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
    liveness = _compute_liveness(
        best_frame_image,
        best_frame_face,
        request.challenge_confidences
    )

    logger.info(f"Match complete — similarity={similarity} liveness={liveness}")

    return MatchResponse(
        similarity_score=similarity,
        liveness_score=liveness
    )