import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("middleware")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start time
        start_time = time.time()
        
        # Log request start
        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log request completion
            self.logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration": duration
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error
            self.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration,
                    "error": str(e)
                },
                exc_info=True
            )
            raise


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for adding security headers"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response 
    



from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

def _get_storage_uri():
    try:
        import redis as redis_lib
        r = redis_lib.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        r.ping()
        return settings.REDIS_URL
    except Exception:
        return "memory://"

def get_user_rate_limit_key(request: Request) -> str:
    """Identify rate limit key by authenticated user, or fallback to client IP."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from app.services.auth import auth_service
            token_data = auth_service.verify_token(token)
            if token_data and token_data.user_id:
                return f"user:{token_data.user_id}"
        except Exception:
            pass
    return get_remote_address(request)

limiter = Limiter(
    key_func=get_user_rate_limit_key,
    storage_uri=_get_storage_uri(),
    default_limits=["200/minute"]
)
