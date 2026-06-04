from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Logging
    log_level: str = "INFO"

    # Image validation
    min_image_width: int = 224
    min_image_height: int = 224

    # Image quality thresholds
    blur_threshold: float = 100.0
    min_brightness: float = 60.0
    max_brightness: float = 220.0

    # Face detection
    min_face_coverage: float = 0.10
    face_detection_size: int = 640

    # Face recognition model (InsightFace)
    face_recognition_model: str = "buffalo_l"

    # Similarity
    similarity_threshold: float = 0.70

    # Challenge verification
    min_frames_per_challenge: int = 5      # minimum usable frames needed
    blink_ear_threshold: float = 0.21      # below = eye closed
    blink_closed_frames: int = 1           # minimum closed frames for valid blink
    head_turn_min_ratio: float = 0.15      # nose deviation ratio for turn detection

    class Config:
        env_file = ".env"
        env_prefix = "FV_"


settings = Settings()