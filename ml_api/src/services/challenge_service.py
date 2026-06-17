import logging
import numpy as np
import cv2
from typing import Optional
import mediapipe as mp
from core.landmark_extractor import extractor, FrameLandmarks
from core.image_utils import decode_base64_image, encode_image_to_base64
from schemas.challenge import ChallengeType
from schemas.photo import Photo
from config import settings

logger = logging.getLogger(__name__)

# Key landmark indices for occlusion detection
_KEY_LANDMARK_INDICES = [1, 33, 263, 61, 291, 168]

_mp_face_mesh = mp.solutions.face_mesh


def _extract_landmarks_from_frames(
    frames: list[Photo]
) -> tuple[list[tuple[np.ndarray, FrameLandmarks, object]], int]:
    """
    Decode each frame and extract landmarks.
    Returns:
        frame_data: list of (image, landmarks, raw_mediapipe_landmarks)
        no_face_count: number of frames where face/landmark extraction failed
    """
    frame_data = []
    no_face_count = 0

    face_mesh = _mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    )

    for frame in frames:
        try:
            image = decode_base64_image(frame.base64)
        except Exception as e:
            logger.warning(f"Frame decode failed: {e}")
            no_face_count += 1
            continue

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            no_face_count += 1
            continue

        raw_landmarks = results.multi_face_landmarks[0]
        h, w = image.shape[:2]
        landmarks = extractor.compute_from_raw(raw_landmarks, h, w)

        if landmarks is None:
            no_face_count += 1
            continue

        frame_data.append((image, landmarks, raw_landmarks))

    face_mesh.close()
    return frame_data, no_face_count


def _analyse_quality(
    frames: list[Photo],
    frame_data: list[tuple[np.ndarray, FrameLandmarks, object]],
    no_face_count: int,
    is_blink: bool
) -> list[str]:
    """
    Analyse quality issues across all frames.
    A reason is reported only if it affects more than half the frames.

    For BLINK: checks blur, brightness, face detection, face size, occlusion.
    For turns: checks blur, brightness, face detection only.
    """
    total = len(frames)
    majority = total / 2

    blur_issues = 0
    brightness_issues = 0
    face_too_far = 0
    face_obscured = 0

    for image, landmarks, raw_landmarks in frame_data:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if blur < settings.blur_threshold:
            blur_issues += 1

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        brightness = float(hsv[:, :, 2].mean())
        if brightness < settings.min_brightness or brightness > settings.max_brightness:
            brightness_issues += 1

        if is_blink:
            # Face size: eye distance relative to image width
            left_eye = raw_landmarks.landmark[33]
            right_eye = raw_landmarks.landmark[263]
            eye_distance = abs(right_eye.x - left_eye.x)
            if eye_distance < settings.eye_distance_threshold:
                face_too_far += 1

            # Occlusion: average visibility of key landmarks
            visibility = sum(
                raw_landmarks.landmark[i].visibility
                for i in _KEY_LANDMARK_INDICES
            ) / len(_KEY_LANDMARK_INDICES)
            if visibility < settings.visibility_threshold:
                face_obscured += 1

    reasons = []
    if no_face_count > majority:
        reasons.append("FACE_NOT_DETECTED")
    if blur_issues > majority:
        reasons.append("BLURRY")
    if brightness_issues > majority:
        reasons.append("POOR_LIGHTING")
    if is_blink and face_too_far > majority:
        reasons.append("FACE_TOO_FAR")
    if is_blink and face_obscured > majority:
        reasons.append("FACE_OBSCURED")

    return reasons


def _score_frame_quality(image: np.ndarray, landmarks: FrameLandmarks) -> float:
    """Score a frame for face matching suitability. Higher = better."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    blur_score = min(blur / settings.blur_threshold, 1.0)
    frontal_score = 1.0 if landmarks.is_frontal else 0.3
    eyes_score = 1.0 if landmarks.eyes_open else 0.0
    return (blur_score * 0.5) + (frontal_score * 0.3) + (eyes_score * 0.2)


def _verify_blink(
    frame_data: list[tuple[np.ndarray, FrameLandmarks, object]]
) -> tuple[bool, float, Optional[np.ndarray]]:
    if len(frame_data) < settings.min_frames_per_challenge:
        return False, 0.0, None

    ears = [lm.avg_ear for _, lm, _ in frame_data]
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

    scored = [
        (i, _score_frame_quality(img, lm))
        for i, (img, lm, _) in enumerate(frame_data)
        if lm.eyes_open and lm.is_frontal
    ]

    best_frame = None
    if scored:
        best_idx = max(scored, key=lambda x: x[1])[0]
        best_frame = frame_data[best_idx][0]

    return detected, round(confidence, 4), best_frame


def _verify_turn(
    frame_data: list[tuple[np.ndarray, FrameLandmarks, object]],
    direction: str
) -> tuple[bool, float]:
    if len(frame_data) < settings.min_frames_per_challenge:
        return False, 0.0

    ratios = [lm.turn_ratio for _, lm, _ in frame_data]

    if direction == "LEFT":
        min_ratio = min(ratios)
        detected = min_ratio < -settings.head_turn_min_ratio
        delta = abs(min_ratio)
    else:
        max_ratio = max(ratios)
        detected = max_ratio > settings.head_turn_min_ratio
        delta = abs(max_ratio)

    confidence = min(delta / settings.head_turn_min_ratio, 1.0) if detected else 0.0
    return detected, round(confidence, 4)


def _verify_smile(
    frame_data: list[tuple[np.ndarray, FrameLandmarks, object]]
) -> tuple[bool, float]:
    """
    Verify smile happened across frames.
    Smile is a sustained state, not a transition — detected when MAR
    exceeds the threshold for at least smile_min_frames frames.
    """
    if len(frame_data) < settings.min_frames_per_challenge:
        return False, 0.0

    mars = [lm.mar for _, lm, _ in frame_data]
    smiling_frames = sum(1 for mar in mars if mar > settings.smile_mar_threshold)

    detected = smiling_frames >= settings.smile_min_frames
    confidence = min(smiling_frames / settings.smile_min_frames, 1.0) if detected else 0.0

    return detected, round(confidence, 4)


def verify(
    challenge_type: ChallengeType,
    frames: list[Photo]
) -> tuple[bool, float, Optional[Photo], list[str]]:
    """
    Main entry point for challenge verification.

    Returns:
        passed: whether challenge was genuinely performed
        confidence: 0.0 - 1.0
        best_frame: Photo object if BLINK passed, None otherwise
        fail_reasons: list of reason codes if failed, empty if passed
    """
    is_blink = challenge_type == ChallengeType.BLINK

    frame_data, no_face_count = _extract_landmarks_from_frames(frames)

    if len(frame_data) < settings.min_frames_per_challenge:
        reasons = _analyse_quality(frames, frame_data, no_face_count, is_blink)
        if not reasons:
            reasons = ["FACE_NOT_DETECTED"]
        logger.warning(
            f"{challenge_type} failed — only {len(frame_data)} usable frames, "
            f"reasons={reasons}"
        )
        return False, 0.0, None, reasons

    if challenge_type == ChallengeType.BLINK:
        detected, confidence, best_frame_image = _verify_blink(frame_data)
        if not detected:
            reasons = _analyse_quality(frames, frame_data, no_face_count, is_blink)
            if not reasons:
                reasons = ["ACTION_NOT_DETECTED"]
            logger.info(f"BLINK failed — reasons={reasons}")
            return False, confidence, None, reasons
        best_frame = None
        if best_frame_image is not None:
            best_frame = Photo(
                base64=encode_image_to_base64(best_frame_image),
                label="best_frame"
            )
        return True, confidence, best_frame, []

    elif challenge_type == ChallengeType.TURN_LEFT:
        detected, confidence = _verify_turn(frame_data, "LEFT")
        if not detected:
            reasons = _analyse_quality(frames, frame_data, no_face_count, is_blink)
            if not reasons:
                reasons = ["ACTION_NOT_DETECTED"]
            logger.info(f"TURN_LEFT failed — reasons={reasons}")
            return False, confidence, None, reasons
        return True, confidence, None, []

    elif challenge_type == ChallengeType.TURN_RIGHT:
        detected, confidence = _verify_turn(frame_data, "RIGHT")
        if not detected:
            reasons = _analyse_quality(frames, frame_data, no_face_count, is_blink)
            if not reasons:
                reasons = ["ACTION_NOT_DETECTED"]
            logger.info(f"TURN_RIGHT failed — reasons={reasons}")
            return False, confidence, None, reasons
        return True, confidence, None, []

    elif challenge_type == ChallengeType.SMILE:
        detected, confidence = _verify_smile(frame_data)
        if not detected:
            reasons = _analyse_quality(frames, frame_data, no_face_count, is_blink)
            if not reasons:
                reasons = ["ACTION_NOT_DETECTED"]
            logger.info(f"SMILE failed — reasons={reasons}")
            return False, confidence, None, reasons
        return True, confidence, None, []

    return False, 0.0, None, ["UNKNOWN_CHALLENGE"]