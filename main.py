"""
PiyP Backend - Main FastAPI Application

Multi-domain architecture with separate domains for:
- Core: Authentication and user management
- RefMan: Reference manager
- Research: AI research agents (future)
- Teaching: Course generation (future)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config.settings import settings


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting PiyP Backend in {settings.environment} mode")
    logger.info(f"API running on port {settings.api_port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PiyP Backend")


# Create FastAPI app
app = FastAPI(
    title="PiyP Backend",
    description="Professor in Your Pocket - AI-powered research and teaching platform",
    version="0.1.0",
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [
        "https://piyp.app",
        "https://www.piyp.app",
        "https://piyp-refman-frontend-production.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "PiyP Backend",
        "version": "0.1.0",
        "environment": settings.environment,
        "domains": {
            "core": "Authentication and user management",
            "refman": "Reference manager",
            "research": "AI research agents (coming soon)",
            "teaching": "Course generation (coming soon)",
        }
    }


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
    }


# Include domain routers
from domains.core import router as core_router
# from domains.refman import router as refman_router  # TODO: Uncomment when refman domain is ready

app.include_router(core_router, prefix="/api/core", tags=["Core"])
# app.include_router(refman_router, prefix="/api/refman", tags=["RefMan"])  # TODO: Uncomment when refman domain is ready


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.is_development
    )