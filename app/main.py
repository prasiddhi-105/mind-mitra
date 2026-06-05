from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware


tags_metadata = [
    {
        "name": "auth",
        "description": "Authentication endpoints. Use /api/v1/auth/login to obtain bearer tokens and /api/v1/auth/refresh to refresh them. Protected routes require an Authorization header: Bearer <access_token>."
    },
    {
        "name": "chat",
        "description": "Chatbot messaging endpoints. These routes are protected and require authentication."
    },
    {
        "name": "emotion",
        "description": "Emotion detection endpoints. These routes are protected and require authentication."
    },
    {
        "name": "journal",
        "description": "Journal management endpoints. These routes are protected and require authentication."
    }
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    setup_logging()
    await init_db()
    yield
    # Shutdown
    # Cleanup resources if needed


app = FastAPI(
    title="MindMitra API",
    description="AI-powered mental wellness backend API.\n\nAuthentication: use /api/v1/auth/login to sign in and receive bearer tokens. Use Authorization: Bearer <token> on protected endpoints. Refresh tokens at /api/v1/auth/refresh.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(RequestLoggingMiddleware)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to MindMitra API",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mindmitra-backend",
        "version": "1.0.0"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "Something went wrong"
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    ) 