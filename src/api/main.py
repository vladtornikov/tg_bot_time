"""FastAPI application main module."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from config.settings import get_settings
from database.connection import async_engine
from models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting up...")
    
    # Create database tables if they don't exist
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created/verified")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await async_engine.dispose()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Telegram Meeting-Scheduler Bot API",
    description="REST API for the Telegram Meeting-Scheduler Bot",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Middleware is now set up in setup_middleware function


# Global exception handler (handled by ErrorHandlerMiddleware)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "0.1.0",
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Telegram Meeting-Scheduler Bot API",
        "version": "0.1.0",
        "docs": "/docs" if settings.is_development else "Documentation not available in production",
    }


# Include routers
from api.routes import oauth, meetings
from api.middleware import setup_middleware

# Setup middleware
setup_middleware(app)

# Include routers
app.include_router(oauth.router)
app.include_router(meetings.router)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
