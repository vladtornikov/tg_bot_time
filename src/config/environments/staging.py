"""Staging environment configuration."""
from src.config.settings import Settings


class StagingSettings(Settings):
    """Staging-specific settings."""
    
    environment: str = "staging"
    debug: bool = False
    reload: bool = False
    
    # Staging logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Staging security
    allowed_hosts: list = ["staging.example.com"]
    
    class Config:
        env_file = ".env.staging"


