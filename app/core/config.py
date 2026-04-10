from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Intelligent School Monitoring System")
    app_env: str = Field(default="development")
    api_v1_str: str = Field(default="/api/v1")
    video_log_dir: str = Field(default="./video_logs")
    video_ttl_hours: int = Field(default=72)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
