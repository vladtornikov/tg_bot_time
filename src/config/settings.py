"""Application settings configuration."""
import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    reload: bool = Field(default=False, env="RELOAD")
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    database_url_sync: str = Field(env="DATABASE_URL_SYNC")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Telegram Bot
    telegram_bot_token: str = Field(env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[str] = Field(default=None, env="TELEGRAM_WEBHOOK_URL")
    telegram_webhook_secret: Optional[str] = Field(default=None, env="TELEGRAM_WEBHOOK_SECRET")
    
    # Google OAuth
    google_client_id: str = Field(env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(env="GOOGLE_REDIRECT_URI")
    
    # Encryption
    encryption_key: str = Field(env="ENCRYPTION_KEY")
    secret_key: str = Field(env="SECRET_KEY")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    
    # Bot Configuration
    bot_host: str = Field(default="0.0.0.0", env="BOT_HOST")
    bot_port: int = Field(default=8080, env="BOT_PORT")
    
    # Worker Configuration
    worker_concurrency: int = Field(default=4, env="WORKER_CONCURRENCY")
    worker_queues: str = Field(default="default,oauth,retry,scheduled", env="WORKER_QUEUES")
    worker_prefetch_multiplier: int = Field(default=1, env="WORKER_PREFETCH_MULTIPLIER")
    worker_max_tasks_per_child: int = Field(default=1000, env="WORKER_MAX_TASKS_PER_CHILD")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Security
    allowed_hosts: List[str] = Field(default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS")
    
    # Monitoring
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    
    @validator("allowed_hosts", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from comma-separated string."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @validator("encryption_key")
    def validate_encryption_key(cls, v):
        """Validate encryption key length."""
        if len(v.encode()) != 32:
            raise ValueError("Encryption key must be exactly 32 bytes")
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging mode."""
        return self.environment == "staging"
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
