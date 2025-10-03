"""Production environment configuration."""
from src.config.settings import Settings


class ProductionSettings(Settings):
    """Production-specific settings."""
    
    environment: str = "production"
    debug: bool = False
    reload: bool = False
    
    # Production logging
    log_level: str = "WARNING"
    log_format: str = "json"
    
    # Production security
    allowed_hosts: list = ["your-domain.com", "www.your-domain.com"]
    
    # Production performance
    api_workers: int = 4
    worker_concurrency: int = 8
    
    class Config:
        env_file = ".env.production"
