from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional

from app.core.config import settings
from app.models.user import (
    User,
    UserCreate,
    UserUpdate,
    Token,
    TokenData,
    UserRole,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
    TokenValidationResponse,
)
from app.services.auth import auth_service
from app.services.notifications import notification_service
from app.core.logging import get_logger

PASSWORD_RESET_RESPONSE = (
    "If an account exists for this email, a reset link has been sent."
)

logger = get_logger("auth_endpoints")

router = APIRouter()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token_data = auth_service.verify_token(token)
        if token_data is None:
            raise credentials_exception
        
        user = await auth_service.get_user_by_id(token_data.user_id)
        if user is None:
            raise credentials_exception
        
        return user
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise credentials_exception



    
async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role — raises 403 for non-admin authenticated users."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.post(
    "/register",
    summary="Register a new user",
    response_model=User,
    responses={
        200: {
            "description": "User registered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "user@example.com",
                        "password_hash": "$2b$12$...",
                        "name": "Marina Sharma",
                        "created_at": "2024-06-02T12:00:00Z"
                    }
                }
            }
        }
    }
)
async def register(
    user_create: UserCreate = Body(
        ...,
        example={
            "email": "user@example.com",
            "name": "Marina Sharma",
            "role": "user",
            "password": "marina@123"
        }
    )
):
    """Register a new user and enter the following details:
        Email,
        Name,
        Role- i.e. the user role,
        Password (string of length 8-100 min-max)"""
    try:
        # Check if user already exists
        existing_user = await auth_service.get_user_by_email(user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user = await auth_service.create_user(user_create)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        logger.info(f"New user registered: {user.email}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/login",
    summary="Login user and return access token",
    response_model=Token,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/x-www-form-urlencoded": {
                    "examples": {
                        "login": {
                            "summary": "Login example",
                            "value": {
                                "username": "user@example.com",
                                "password": "SecurePass123"
                            }
                        }
                    }
                }
            }
        },
        "responses": {
            "200": {
                "description": "Login successful",
                "content": {
                    "application/json": {
                        "example": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "expires_in": 1800
                        }
                    }
                }
            }
        }
    }
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login user and enter the following details:
        Email,
        Password"""
    try:
        # Authenticate user
        user = await auth_service.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        # Create tokens
        access_token = auth_service.create_access_token(
            data={"sub": user.email, "user_id": user.id, "role": user.role}
        )
        refresh_token = auth_service.create_refresh_token(
            data={"sub": user.email, "user_id": user.id, "role": user.role}
        )
        
        logger.info(f"User logged in: {user.email}")
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60  # 30 minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/refresh",
    summary="Refresh access token",
    response_model=Token,
    responses={
        200: {
            "description": "New token pair returned",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "expires_in": 1800
                    }
                }
            }
        }
    }
)
async def refresh_token(refresh_token: str = Body(
    ...,
    example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
)):
    """Refresh access token using refresh token:
        Enter the refresh access token generated after revisting or refreshing the page after
        Note: This is different from the login access token"""
    try:
        # Verify refresh token
        token_data = auth_service.verify_token(refresh_token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        user = await auth_service.get_user_by_id(token_data.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user"
            )
        
        # Create new tokens
        access_token = auth_service.create_access_token(
            data={"sub": user.email, "user_id": user.id, "role": user.role}
        )
        new_refresh_token = auth_service.create_refresh_token(
            data={"sub": user.email, "user_id": user.id, "role": user.role}
        )
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=30 * 60  # 30 minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/profile",
    summary="Get current user profile",
    response_model=User,
    responses={
        200: {
            "description": "Current authenticated user profile",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "user@example.com",
                        "password_hash": "$2b$12$...",
                        "name": "Sofie dsouza",
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                }
            }
        }
    }
)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile and enter the following details:
        Authorization: Bearer <access_token>"""
    return current_user


@router.put(
    "/profile",
    summary="Update current user profile",
    response_model=User,
)
async def update_profile(
    user_update: UserUpdate = Body(...),
    current_user: User = Depends(get_current_user),
):
    """Update name, emergency contacts, or profile picture URL."""
    try:
        updated_user = await auth_service.update_user(current_user.id, user_update)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        logger.info(f"Profile updated for user: {current_user.email}")
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@router.post(
    "/profile/picture",
    summary="Upload profile picture",
    response_model=User,
)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload and save a profile picture for the current user."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: JPEG, PNG, WebP, GIF",
        )

    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    try:
        upload_dir = Path(settings.UPLOAD_DIR) / "profile_pictures"
        upload_dir.mkdir(parents=True, exist_ok=True)

        extension = IMAGE_EXTENSIONS.get(file.content_type, ".jpg")
        filename = f"{current_user.id}{extension}"
        file_path = upload_dir / filename

        with open(file_path, "wb") as f:
            f.write(contents)

        profile_picture_url = f"/uploads/profile_pictures/{filename}"
        updated_user = await auth_service.update_user(
            current_user.id,
            UserUpdate(profile_picture_url=profile_picture_url),
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save profile picture",
            )

        logger.info(f"Profile picture uploaded for user: {current_user.email}")
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile picture upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload profile picture",
        )


@router.post(
    "/forgot-password",
    summary="Request a password reset email",
    response_model=MessageResponse,
)
async def forgot_password(request: ForgotPasswordRequest):
    """Send a password reset link if the email belongs to an active account."""
    try:
        user = await auth_service.get_user_by_email(request.email)
        if user and user.is_active:
            raw_token = await auth_service.create_password_reset_token(user.id)
            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
            await notification_service.send_password_reset_email(
                user.email, user.name, reset_link
            )
            logger.info(f"Password reset requested for: {user.email}")
        return MessageResponse(message=PASSWORD_RESET_RESPONSE)
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/reset-password/validate",
    summary="Validate a password reset token",
    response_model=TokenValidationResponse,
)
async def validate_reset_password_token(token: str):
    """Check whether a reset token is valid and not expired."""
    valid = await auth_service.validate_reset_token(token)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return TokenValidationResponse(valid=True)


@router.post(
    "/reset-password",
    summary="Reset password using a valid token",
    response_model=MessageResponse,
)
async def reset_password(request: ResetPasswordRequest):
    """Set a new password using a valid, unexpired reset token."""
    try:
        success = await auth_service.reset_password(
            request.token, request.new_password
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )
        logger.info("Password reset completed successfully")
        return MessageResponse(message="Password reset successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/logout",
    summary="Logout user",
    responses={
        200: {
            "description": "Successfully logged out",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Successfully logged out"
                    }
                }
            }
        }
    }
)
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user and enter the following details:
        Authorization: Bearer <access_token>"""
    # In a real implementation, you might want to blacklist the token
    # For now, we'll just return a success message
    logger.info(f"User logged out: {current_user.email}")
    return {"message": "Successfully logged out"} 