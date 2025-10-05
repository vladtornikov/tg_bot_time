"""Production environment configuration."""

from src.config.settings import Settings


class ProductionSettings(Settings):
    """Production-specific settings."""
    
    # Environment
    environment: str = "production"
    debug: bool = False
    reload: bool = False
    
    # Security
    allowed_hosts: list = ["yourdomain.com", "api.yourdomain.com", "bot.yourdomain.com"]
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    # Bot Configuration
    bot_host: str = "0.0.0.0"
    bot_port: int = 8080
    
    # Worker Configuration
    worker_concurrency: int = 8
    worker_prefetch_multiplier: int = 1
    worker_max_tasks_per_child: int = 1000
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Monitoring
    prometheus_port: int = 9090
    grafana_port: int = 3000
    
    # Security Headers
    enable_security_headers: bool = True
    enable_rate_limiting: bool = True
    rate_limit_per_minute: int = 60
    
    # SSL/TLS
    enable_ssl: bool = True
    ssl_cert_path: str = "/etc/ssl/certs/yourdomain.com.crt"
    ssl_key_path: str = "/etc/ssl/private/yourdomain.com.key"
    
    # Database
    database_pool_size: int = 20
    database_max_overflow: int = 30
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600
    
    # Redis
    redis_max_connections: int = 100
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5
    
    # Caching
    enable_redis_cache: bool = True
    cache_default_timeout: int = 300
    cache_key_prefix: str = "tg_bot:"
    
    # Session Management
    session_secret_key: str = None  # Will be set from environment
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "strict"
    session_expires_in: int = 86400  # 24 hours
    
    # OAuth Security
    oauth_state_expiry: int = 600  # 10 minutes
    oauth_token_encryption_key: str = None  # Will be set from environment
    
    # Rate Limiting
    rate_limit_storage: str = "redis"
    rate_limit_strategy: str = "fixed-window"
    
    # Health Checks
    health_check_timeout: int = 5
    health_check_interval: int = 30
    
    # Performance
    enable_compression: bool = True
    compression_min_size: int = 1024
    enable_gzip: bool = True
    
    # CORS
    cors_origins: list = ["https://yourdomain.com", "https://admin.yourdomain.com"]
    cors_methods: list = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: list = ["Authorization", "Content-Type", "X-Requested-With"]
    
    # Monitoring and Alerting
    enable_metrics: bool = True
    metrics_path: str = "/metrics"
    enable_health_checks: bool = True
    health_check_path: str = "/health"
    
    # Error Reporting
    enable_error_reporting: bool = True
    error_reporting_dsn: str = None  # Will be set from environment (e.g., Sentry DSN)
    
    # Backup Configuration
    enable_database_backups: bool = True
    backup_retention_days: int = 30
    backup_schedule: str = "0 2 * * *"  # Daily at 2 AM
    
    # File Storage
    file_storage_backend: str = "local"  # or "s3", "gcs"
    file_storage_path: str = "/var/lib/tg_bot/files"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # Email Configuration (for notifications)
    enable_email_notifications: bool = False
    smtp_host: str = None
    smtp_port: int = 587
    smtp_username: str = None
    smtp_password: str = None
    smtp_use_tls: bool = True
    
    # External Service Timeouts
    telegram_api_timeout: int = 30
    google_api_timeout: int = 30
    database_query_timeout: int = 30
    
    # Resource Limits
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    max_response_size: int = 50 * 1024 * 1024  # 50MB
    
    # Development vs Production
    enable_debug_toolbar: bool = False
    enable_api_docs: bool = False  # Disable in production for security
    enable_swagger_ui: bool = False
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env.production"
        env_file_encoding = "utf-8"
        case_sensitive = False
        validate_assignment = True