import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from typing import Optional
from config import settings


# MediaPipe landmark indices
LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
LEFT_EYE_LEFT = 33
LEFT_EYE_RIGHT = 133

RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374
RIGHT_EYE_LEFT = 362
RIGHT_EYE_RIGHT = 263

NOSE_TIP = 1
LEFT_EYE_CORNER = 33
RIGHT_EYE_CORNER = 263


@dataclass
class FrameLandmarks:
    # Eye aspect ratios
    left_ear: float
    right_ear: float
    avg_ear: float
    eyes_open: bool

    # Head turn — nose deviation ratio
    # 0.0 = centered, negative = turned left, positive = turned right
    # range roughly -0.5 to 0.5 for significant turns
    turn_ratio: float

    # Quality signals
    is_frontal: bool


class LandmarkExtractor:
    def __init__(self):
        mp_face_mesh = mp.solutions.face_mesh
        self._face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )

    def extract(self, image: np.ndarray) -> Optional[FrameLandmarks]:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return None

        landmarks = results.multi_face_landmarks[0]
        h, w = image.shape[:2]

        left_ear = self._eye_aspect_ratio(
            landmarks, LEFT_EYE_TOP, LEFT_EYE_BOTTOM,
            LEFT_EYE_LEFT, LEFT_EYE_RIGHT, h, w
        )
        right_ear = self._eye_aspect_ratio(
            landmarks, RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM,
            RIGHT_EYE_LEFT, RIGHT_EYE_RIGHT, h, w
        )
        avg_ear = (left_ear + right_ear) / 2.0

        turn_ratio = self._estimate_turn_ratio(landmarks)

        from config import settings
        eyes_open = avg_ear > settings.blink_ear_threshold
        is_frontal = abs(turn_ratio) < 0.1

        return FrameLandmarks(
            left_ear=left_ear,
            right_ear=right_ear,
            avg_ear=avg_ear,
            eyes_open=eyes_open,
            turn_ratio=turn_ratio,
            is_frontal=is_frontal
        )

    def _eye_aspect_ratio(self, landmarks, top: int, bottom: int,
                          left: int, right: int, h: int, w: int) -> float:
        def lm(idx):
            p = landmarks.landmark[idx]
            return np.array([p.x * w, p.y * h])

        vertical = np.linalg.norm(lm(top) - lm(bottom))
        horizontal = np.linalg.norm(lm(left) - lm(right))

        if horizontal == 0:
            return 0.0
        return vertical / horizontal

    def _estimate_turn_ratio(self, landmarks) -> float:
        """
        Nose deviation ratio relative to eye center.
        0.0 = centered
        Negative = turned left
        Positive = turned right
        """
        nose = landmarks.landmark[NOSE_TIP]
        left_eye = landmarks.landmark[LEFT_EYE_CORNER]
        right_eye = landmarks.landmark[RIGHT_EYE_CORNER]

        eye_center_x = (left_eye.x + right_eye.x) / 2
        eye_width = abs(right_eye.x - left_eye.x)

        if eye_width == 0:
            return 0.0

        return (nose.x - eye_center_x) / eye_width
    
    def compute_from_raw(self, raw_landmarks, h: int, w: int) -> FrameLandmarks:
        """
        Compute FrameLandmarks from already-extracted MediaPipe landmarks.
        Use this when you've already run FaceMesh and have the raw result.
        """

        left_ear = self._eye_aspect_ratio(
            raw_landmarks, LEFT_EYE_TOP, LEFT_EYE_BOTTOM,
            LEFT_EYE_LEFT, LEFT_EYE_RIGHT, h, w
        )
        right_ear = self._eye_aspect_ratio(
            raw_landmarks, RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM,
            RIGHT_EYE_LEFT, RIGHT_EYE_RIGHT, h, w
        )
        avg_ear = (left_ear + right_ear) / 2.0
        turn_ratio = self._estimate_turn_ratio(raw_landmarks)
        eyes_open = avg_ear > settings.blink_ear_threshold
        is_frontal = abs(turn_ratio) < settings.frontal_turn_ratio_threshold

        return FrameLandmarks(
            left_ear=left_ear,
            right_ear=right_ear,
            avg_ear=avg_ear,
            eyes_open=eyes_open,
            turn_ratio=turn_ratio,
            is_frontal=is_frontal
        )

# Singleton
extractor = LandmarkExtractor()