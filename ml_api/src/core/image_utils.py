import base64
import cv2
import numpy as np
from config import settings


def decode_base64_image(base64_string: str) -> np.ndarray:
    image_bytes = base64.b64decode(base64_string)
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Image could not be decoded.")

    image = _ensure_bgr(image)

    h, w = image.shape[:2]
    if w < settings.min_image_width or h < settings.min_image_height:
        raise ValueError(
            f"Image too small: {w}x{h}. "
            f"Minimum is {settings.min_image_width}x{settings.min_image_height}."
        )

    return image


def resize_for_processing(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]

    if max(h, w) <= settings.face_detection_size:
        return image

    scale = settings.face_detection_size / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)

    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def encode_image_to_base64(image: np.ndarray) -> str:
    _, buffer = cv2.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")


def _ensure_bgr(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    return image