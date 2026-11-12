from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    APP_NAME: str = "DrumScript API"
    VERSION: str = "0.2.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://drumuser:drumpass@postgres:5432/drumtranscribe"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]

    # Uploads and results live under DATA_DIR/jobs/<job id>/ on a volume shared with the ML worker.
    DATA_DIR: str = "/data"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024
    ALLOWED_AUDIO_FORMATS: list[str] = ["mp3", "wav", "m4a", "flac"]


settings = Settings()
