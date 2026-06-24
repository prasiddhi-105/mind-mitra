from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis import init_redis, close_redis, ping_redis
from app.api.v1.api import api_router
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware, limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


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
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    (Path(settings.UPLOAD_DIR) / "profile_pictures").mkdir(parents=True, exist_ok=True)
    await init_db()
    await init_redis()
    yield
    await close_redis()
    await close_db()


app = FastAPI(
    title="MindMitra API",
    description="AI-powered mental wellness backend API.\n\nAuthentication: use /api/v1/auth/login to sign in and receive bearer tokens. Use Authorization: Bearer <token> on protected endpoints. Refresh tokens at /api/v1/auth/refresh.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

# Rate limiting
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    retry_after = (exc.headers or {}).get("Retry-After", "60")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": retry_after},
        content={"error": "rate_limit_exceeded", "message": f"Too many requests. Retry after {retry_after} seconds.", "retry_after": int(retry_after)}
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

# Serve uploaded files (profile pictures, etc.)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


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
    redis_ok = await ping_redis()
    return {
        "status": "healthy",
        "service": "mindmitra-backend",
        "version": "1.0.0",
        "redis": "connected" if redis_ok else "unavailable",
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
