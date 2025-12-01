"""
FastAPI main application entry point.
CaseMind Web App - Legal Case Similarity Search (Search-Only Interface).
"""

import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.database import db
from api.routers import search, cases, health
from utils.helpers import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Handles startup and shutdown.
    """
    # Startup
    logger.info("Starting CaseMind Web API...")
    await db.connect()
    logger.info("CaseMind Web API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down CaseMind Web API...")
    await db.disconnect()
    logger.info("CaseMind Web API shut down")


# Create FastAPI application
app = FastAPI(
    title="CaseMind API",
    description="Legal Case Similarity Search API - Search-only interface for finding similar cases",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An unexpected error occurred"
        }
    )


# Include routers
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["Cases"])
app.include_router(health.router, prefix="/api/v1", tags=["Health"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "CaseMind API",
        "version": "1.0.0",
        "description": "Legal Case Similarity Search",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


# Setup logging
setup_logging("INFO", disable=False)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
