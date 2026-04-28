from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Intelligent School Monitoring System")
    app_env: str = Field(default="development")
    api_v1_str: str = Field(default="/api/v1")
    video_log_dir: str = Field(default="./video_logs")
    video_ttl_hours: int = Field(default=72)

    # ── Live camera ingestion ─────────────────────────────────────────────
    # Path to a JSON file listing real cameras to auto-register on startup.
    # Format: [{"camera_id":"...","zone_id":"...","label":"...","source_url":"..."}]
    # `source_url` may be an RTSP URL, an HTTP MJPEG URL, an integer index for
    # a USB webcam ("0"), or a local video file path.
    # If the file does not exist, no real cameras are registered (demo mode).
    camera_sources_file: str = Field(default="./cameras.json")
    camera_reconnect_seconds: float = Field(default=5.0)
    camera_jpeg_quality: int = Field(default=70)            # 1-100, lower = smaller
    camera_max_fps: float = Field(default=15.0)             # cap streaming/processing
    camera_anonymize_faces: bool = Field(default=True)      # Unit 14 governance
    camera_open_timeout_seconds: float = Field(default=10.0)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
