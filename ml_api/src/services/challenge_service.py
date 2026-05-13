import logging
import numpy as np
import cv2
from typing import Optional
from core.landmark_extractor import extractor, FrameLandmarks
from core.image_utils import decode_base64_image, encode_image_to_base64
from schemas.challenge import ChallengeType
from schemas.photo import Photo
from config import settings

logger = logging.getLogger(__name__)


def _extract_landmarks_from_frames(frames: list[Photo]) -> list[tuple[np.ndarray, FrameLandmarks]]:
    """
    Decode each frame and extract landmarks.
    Returns list of (image, landmarks) pairs.
    Frames that fail decoding or landmark extraction are skipped.
    """
    results = []
    for frame in frames:
        try:
            image = decode_base64_image(frame.base64)
            landmarks = extractor.extract(image)
            if landmarks is not None:
                results.append((image, landmarks))
        except Exception as e:
            logger.warning(f"Frame skipped: {e}")
    return results


def _score_frame_quality(image: np.ndarray, landmarks: FrameLandmarks) -> float:
    """
    Score a frame for face matching suitability.
    Higher = better frame to use for ArcFace matching.
    Only useful for BLINK challenge where we extract the best frame.
    """
    # Blur score
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    blur_score = min(blur / settings.blur_threshold, 1.0)

    # Frontality score
    frontal_score = 1.0 if landmarks.is_frontal else 0.3

    # Eyes open score
    eyes_score = 1.0 if landmarks.eyes_open else 0.0

    return (blur_score * 0.5) + (frontal_score * 0.3) + (eyes_score * 0.2)


def _verify_blink(
    frame_data: list[tuple[np.ndarray, FrameLandmarks]]
) -> tuple[bool, float, Optional[np.ndarray]]:
    """
    Verify blink happened across frames.
    Returns: (detected, confidence, best_frame_image)

    Blink = eyes open → eyes closed → eyes open transition.
    Best frame = highest quality open-eye frontal frame.
    """
    if len(frame_data) < settings.min_frames_per_challenge:
        return False, 0.0, None

    ears = [lm.avg_ear for _, lm in frame_data]
    closed_indices = [
        i for i, ear in enumerate(ears)
        if ear < settings.blink_ear_threshold
    ]

    if not closed_indices:
        return False, 0.0, None

    first_closed = closed_indices[0]
    last_closed = closed_indices[-1]

    has_open_before = any(
        ears[i] > settings.blink_ear_threshold
        for i in range(first_closed)
    )
    has_open_after = any(
        ears[i] > settings.blink_ear_threshold
        for i in range(last_closed + 1, len(ears))
    )

    detected = has_open_before and has_open_after

    if not detected:
        return False, 0.0, None

    confidence = min(len(closed_indices) / settings.blink_closed_frames, 1.0)

    # Select best frame — highest quality open-eye frontal frame
    scored = [
        (i, _score_frame_quality(img, lm))
        for i, (img, lm) in enumerate(frame_data)
        if lm.eyes_open and lm.is_frontal
    ]

    best_frame = None
    if scored:
        best_idx = max(scored, key=lambda x: x[1])[0]
        best_frame = frame_data[best_idx][0]

    return detected, round(confidence, 4), best_frame


def _verify_turn(
    frame_data: list[tuple[np.ndarray, FrameLandmarks]],
    direction: str
) -> tuple[bool, float]:
    """
    Verify head turn happened across frames.
    direction: "LEFT" or "RIGHT"

    TURN_LEFT: yaw goes negative
    TURN_RIGHT: yaw goes positive
    """
    if len(frame_data) < settings.min_frames_per_challenge:
        return False, 0.0

    yaws = [lm.yaw for _, lm in frame_data]

    if direction == "LEFT":
        min_yaw = min(yaws)
        detected = min_yaw < -settings.head_turn_min_degrees
        delta = abs(min_yaw)
    else:
        max_yaw = max(yaws)
        detected = max_yaw > settings.head_turn_min_degrees
        delta = abs(max_yaw)

    confidence = min(delta / settings.head_turn_min_degrees, 1.0) if detected else 0.0

    return detected, round(confidence, 4)


def verify(
    challenge_type: ChallengeType,
    frames: list[Photo]
) -> tuple[bool, float, Optional[Photo]]:
    """
    Main entry point for challenge verification.

    Returns:
        passed: whether challenge was genuinely performed
        confidence: 0.0 - 1.0
        best_frame: Photo object if BLINK, None otherwise
    """
    frame_data = _extract_landmarks_from_frames(frames)

    if len(frame_data) < settings.min_frames_per_challenge:
        logger.warning(
            f"{challenge_type} failed — only {len(frame_data)} usable frames "
            f"out of {len(frames)} received."
        )
        return False, 0.0, None

    if challenge_type == ChallengeType.BLINK:
        detected, confidence, best_frame_image = _verify_blink(frame_data)
        best_frame = None
        if detected and best_frame_image is not None:
            best_frame = Photo(
                base64=encode_image_to_base64(best_frame_image),
                label="best_frame"
            )
        return detected, confidence, best_frame

    elif challenge_type == ChallengeType.TURN_LEFT:
        detected, confidence = _verify_turn(frame_data, "LEFT")
        return detected, confidence, None

    elif challenge_type == ChallengeType.TURN_RIGHT:
        detected, confidence = _verify_turn(frame_data, "RIGHT")
        return detected, confidence, None

    return False, 0.0, None