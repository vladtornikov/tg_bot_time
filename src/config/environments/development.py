"""Development environment configuration."""
from src.config.settings import Settings


class DevelopmentSettings(Settings):
    """Development-specific settings."""
    
    environment: str = "development"
    debug: bool = True
    reload: bool = True
    
    # Use local services
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/tg_bot_dev"
    database_url_sync: str = "postgresql://user:password@localhost:5432/tg_bot_dev"
    redis_url: str = "redis://localhost:6379/0"
    
    # Development logging
    log_level: str = "DEBUG"
    log_format: str = "text"
    
    # Relaxed security for development
    allowed_hosts: list = ["*"]
    
    class Config:
        env_file = ".env.development"


