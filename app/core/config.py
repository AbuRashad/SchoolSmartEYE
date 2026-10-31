from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_JWT_SECRET = "change-me-in-production"
DEFAULT_DEMO_PASSWORDS = {
    "teacher": "teacher123",
    "principal": "principal123",
    "ministry": "ministry123",
}


class Settings(BaseSettings):
    app_name: str = Field(default="Intelligent School Monitoring System")
    app_env: str = Field(default="development")
    api_v1_str: str = Field(default="/api/v1")
    video_log_dir: str = Field(default="./video_logs")
    video_ttl_hours: int = Field(default=72)

    # ── Database ──────────────────────────────────────────────────────────
    # Any SQLAlchemy URL. SQLite by default; for PostgreSQL use e.g.
    # postgresql+psycopg://USER:PASSWORD@localhost:5432/schoolsmarteye (needs a driver, e.g. psycopg).
    database_url: str = Field(default="sqlite:///./schoolsmarteye.db")
    # Create missing tables on startup. Set to false when schema is managed by
    # Alembic (`alembic upgrade head`).
    db_auto_create: bool = Field(default=True)
    # Independent PostgreSQL target for the empty next-generation database.
    # Leave unset until a separate database has been provisioned.
    next_database_url: str = Field(default="")

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

    # ── Authentication (JWT) ──────────────────────────────────────────────
    # Override JWT_SECRET_KEY in every real deployment (e.g. `openssl rand -hex 32`).
    # The app refuses to start with the default secret when APP_ENV=production.
    jwt_secret_key: str = Field(default=DEFAULT_JWT_SECRET)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)

    # Demo accounts created on first start when the users table is empty.
    seed_demo_users: bool = Field(default=True)
    demo_teacher_password: str = Field(default=DEFAULT_DEMO_PASSWORDS["teacher"])
    demo_principal_password: str = Field(default=DEFAULT_DEMO_PASSWORDS["principal"])
    demo_ministry_password: str = Field(default=DEFAULT_DEMO_PASSWORDS["ministry"])

    # ── CORS ──────────────────────────────────────────────────────────────
    # Comma-separated list of allowed browser origins.
    cors_origins: str = Field(default="http://127.0.0.1:5173,http://localhost:5173")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_for_production(self) -> None:
        """Fail loudly if insecure defaults are used in production."""
        if self.is_production and self.jwt_secret_key == DEFAULT_JWT_SECRET:
            raise RuntimeError(
                "JWT_SECRET_KEY is still the insecure default while APP_ENV=production. "
                "Set a strong random JWT_SECRET_KEY (e.g. `openssl rand -hex 32`)."
            )
        if self.is_production and len(self.jwt_secret_key) < 32:
            raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters in production.")


settings = Settings()
