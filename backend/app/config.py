from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Drum Transcription API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # Database
    DATABASE_URL: str = "postgresql://drumuser:drumpass@postgres:5432/drumtranscribe"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_AUDIO_FORMATS: list[str] = ["mp3", "wav", "m4a"]
    UPLOAD_DIR: str = "/app/uploads"
    
    # Processing
    MAX_AUDIO_DURATION: int = 360  # 6 minutes in seconds
    PROCESSING_TIMEOUT: int = 300  # 5 minutes
    
    # Auth0 (optional)
    AUTH0_DOMAIN: Optional[str] = None
    AUTH0_AUDIENCE: Optional[str] = None
    AUTH0_CLIENT_ID: Optional[str] = None
    
    # AWS (for production)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # Subscription Tiers
    FREE_TIER_MONTHLY_LIMIT: int = 3
    FREE_TIER_MAX_DURATION: int = 120  # 2 minutes
    BASIC_TIER_MAX_DURATION: int = 360  # 6 minutes
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()