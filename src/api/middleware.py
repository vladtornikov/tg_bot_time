"""API middleware for security, logging, and error handling."""
import time
import uuid
import logging
from typing import Callable, Optional

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logging middleware for request/response logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Log request
        start_time = time.time()
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "content_length": request.headers.get("content-length"),
            },
        )
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": process_time,
                "response_size": response.headers.get("content-length"),
            },
        )
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Add HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(self, app, max_requests: int = 100, time_window: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}  # In production, use Redis
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get current time
        current_time = time.time()
        
        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if current_time - req_time < self.time_window
            ]
        else:
            self.requests[client_ip] = []
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.max_requests} per {self.time_window} seconds",
                    "retry_after": self.time_window,
                },
                headers={"Retry-After": str(self.time_window)},
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        return await call_next(request)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for API requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip authentication for certain paths
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Check for API key in headers
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            # For now, allow requests without API key
            # In production, you would validate the API key
            return await call_next(request)
        
        # Validate API key (implement your validation logic)
        if not self.validate_api_key(api_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Invalid API key",
                    "message": "The provided API key is invalid",
                },
            )
        
        # Add user info to request state
        request.state.api_key = api_key
        request.state.authenticated = True
        
        return await call_next(request)
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key."""
        # Implement your API key validation logic
        # For now, accept any non-empty key
        return bool(api_key and len(api_key) > 10)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Error handling middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except HTTPException as e:
            # Handle HTTP exceptions
            logger.warning(
                f"HTTP exception: {e.status_code} - {e.detail}",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "method": request.method,
                    "url": str(request.url),
                },
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": "HTTP Error",
                    "message": e.detail,
                    "status_code": e.status_code,
                },
            )
        except Exception as e:
            # Handle unexpected exceptions
            logger.error(
                f"Unexpected error: {e}",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "method": request.method,
                    "url": str(request.url),
                },
                exc_info=True,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "status_code": 500,
                },
            )


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware for cross-origin requests."""
    
    def __init__(self, app, allow_origins: list = None, allow_methods: list = None, allow_headers: list = None):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["*"]
        self.allow_headers = allow_headers or ["*"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = ", ".join(self.allow_origins)
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
            response.headers["Access-Control-Max-Age"] = "86400"
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = ", ".join(self.allow_origins)
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Request validation middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Validate request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": "Request too large",
                    "message": "Request size exceeds 10MB limit",
                },
            )
        
        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={
                        "error": "Unsupported media type",
                        "message": "Content-Type must be application/json",
                    },
                )
        
        return await call_next(request)


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """Health check middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Handle health check requests
        if request.url.path == "/health":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "healthy",
                    "timestamp": time.time(),
                    "version": "0.1.0",
                    "environment": settings.environment,
                },
            )
        
        return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Metrics collection middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Update metrics
        self.request_count += 1
        if response.status_code >= 400:
            self.error_count += 1
        
        self.response_times.append(response_time)
        if len(self.response_times) > 1000:  # Keep only last 1000 requests
            self.response_times = self.response_times[-1000:]
        
        # Add metrics headers
        response.headers["X-Request-Count"] = str(self.request_count)
        response.headers["X-Error-Count"] = str(self.error_count)
        response.headers["X-Avg-Response-Time"] = str(
            sum(self.response_times) / len(self.response_times) if self.response_times else 0
        )
        
        return response


def setup_middleware(app):
    """Setup all middleware for the FastAPI application."""
    # Add middleware in order (last added is first executed)
    
    # Health check middleware (should be first)
    app.add_middleware(HealthCheckMiddleware)
    
    # Error handling middleware
    app.add_middleware(ErrorHandlerMiddleware)
    
    # Request validation middleware
    app.add_middleware(RequestValidationMiddleware)
    
    # Authentication middleware
    app.add_middleware(AuthenticationMiddleware)
    
    # Rate limiting middleware
    app.add_middleware(RateLimitMiddleware, max_requests=100, time_window=60)
    
    # CORS middleware
    app.add_middleware(CORSMiddleware)
    
    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    # Gzip compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Trusted host middleware for production
    if not settings.is_development:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)