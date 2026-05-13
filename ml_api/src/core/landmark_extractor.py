import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from typing import Optional


# MediaPipe landmark indices
# Left eye
LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
LEFT_EYE_LEFT = 33
LEFT_EYE_RIGHT = 133

# Right eye
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374
RIGHT_EYE_LEFT = 362
RIGHT_EYE_RIGHT = 263

# Head pose reference points
NOSE_TIP = 1
CHIN = 199
LEFT_EYE_CORNER = 33
RIGHT_EYE_CORNER = 263
LEFT_MOUTH = 61
RIGHT_MOUTH = 291


@dataclass
class FrameLandmarks:
    # Eye aspect ratios
    left_ear: float
    right_ear: float
    avg_ear: float
    eyes_open: bool

    # Head pose
    yaw: float    # left/right rotation, negative = turned left
    pitch: float  # up/down rotation, negative = looking up

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

        yaw, pitch = self._estimate_head_pose(landmarks, h, w)

        from config import settings
        eyes_open = avg_ear > settings.blink_ear_threshold
        is_frontal = abs(yaw) < 15.0 and abs(pitch) < 15.0

        return FrameLandmarks(
            left_ear=left_ear,
            right_ear=right_ear,
            avg_ear=avg_ear,
            eyes_open=eyes_open,
            yaw=yaw,
            pitch=pitch,
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

    def _estimate_head_pose(self, landmarks, h: int, w: int):
        def lm2d(idx):
            p = landmarks.landmark[idx]
            return np.array([p.x * w, p.y * h])

        model_points = np.array([
            [0.0, 0.0, 0.0],
            [0.0, -330.0, -65.0],
            [-225.0, 170.0, -135.0],
            [225.0, 170.0, -135.0],
            [-150.0, -150.0, -125.0],
            [150.0, -150.0, -125.0],
        ], dtype=np.float64)

        image_points = np.array([
            lm2d(NOSE_TIP),
            lm2d(CHIN),
            lm2d(LEFT_EYE_CORNER),
            lm2d(RIGHT_EYE_CORNER),
            lm2d(LEFT_MOUTH),
            lm2d(RIGHT_MOUTH),
        ], dtype=np.float64)

        focal_length = w
        camera_matrix = np.array([
            [focal_length, 0, w / 2],
            [0, focal_length, h / 2],
            [0, 0, 1]
        ], dtype=np.float64)

        dist_coeffs = np.zeros((4, 1))

        success, rotation_vec, _ = cv2.solvePnP(
            model_points, image_points,
            camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return 0.0, 0.0

        rotation_mat, _ = cv2.Rodrigues(rotation_vec)
        yaw = float(np.degrees(np.arctan2(rotation_mat[1, 0], rotation_mat[0, 0])))
        pitch = float(np.degrees(np.arctan2(
            -rotation_mat[2, 0],
            np.sqrt(rotation_mat[2, 1] ** 2 + rotation_mat[2, 2] ** 2)
        )))

        return yaw, pitch


# Singleton
extractor = LandmarkExtractor()