from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    secret_key: str = "dev-secret-key-change-me"
    port: int = 8000
    ffmpeg_path: str = "ffmpeg"
    max_disk_usage_gb: int = 100

    class Config:
        env_file = ".env"

settings = Settings()