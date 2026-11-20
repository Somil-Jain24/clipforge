from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "ClipForge AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    # Supports SQLite for local dev/testing and Supabase PostgreSQL for production
    DATABASE_URL: str = "sqlite+aiosqlite:///./clipforge.db"
    # Sync database URL for synchronous workers/tools when needed
    SYNC_DATABASE_URL: str = "sqlite:///./clipforge.db"
    
    # Worker & Security
    WORKER_SECRET: str = "clipforge-default-worker-secret-change-me"
    LEASE_DURATION_SECONDS: int = 60
    HEARTBEAT_INTERVAL_SECONDS: int = 15
    MAX_JOB_RETRIES: int = 3
    DEFAULT_CHUNK_DURATION: int = 120  # seconds
    
    # Storage
    STORAGE_DIR: str = os.path.abspath("./storage")
    UPLOAD_MAX_BYTES: int = 500 * 1024 * 1024  # 500 MB max video upload
    
    # Telegram Bot Notifications (Optional)
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    # Public Dashboard URL (for Telegram links)
    DASHBOARD_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
