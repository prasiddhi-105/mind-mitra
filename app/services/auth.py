from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
import secrets
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.models.user import User, UserCreate, UserInDB, UserUpdate, TokenData, UserRole
from app.core.database import get_collection
from app.core.logging import get_logger

logger = get_logger("auth")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service"""
    
    def __init__(self):
        self._users_collection = None
        self._reset_tokens_collection = None
    
    @staticmethod
    def _hash_reset_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()
    
    @property
    def users_collection(self):
        """Get users collection lazily"""
        if self._users_collection is None:
            self._users_collection = get_collection("users")
        return self._users_collection
    
    @property
    def reset_tokens_collection(self):
        """Get password reset tokens collection lazily"""
        if self._reset_tokens_collection is None:
            self._reset_tokens_collection = get_collection("password_reset_tokens")
        return self._reset_tokens_collection
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            role: str = payload.get("role")
            
            if email is None or user_id is None:
                return None
            
            return TokenData(email=email, user_id=user_id, role=UserRole(role))
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            return None
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        try:
            user_doc = await self.users_collection.find_one({"email": email})
            if not user_doc:
                return None
            
            if not self.verify_password(password, user_doc["hashed_password"]):
                return None
            
            return User(**user_doc)
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def create_user(self, user_create: UserCreate) -> Optional[User]:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = await self.users_collection.find_one({"email": user_create.email})
            if existing_user:
                return None
            
            # Create user document
            user_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            user_doc = {
                "id": user_id,
                "email": user_create.email,
                "name": user_create.name,
                "role": user_create.role,
                "hashed_password": self.get_password_hash(user_create.password),
                "emergency_contacts": [],
                "is_active": True,
                "created_at": now,
                "updated_at": now
            }
            
            result = await self.users_collection.insert_one(user_doc)
            if result.inserted_id:
                return User(**user_doc)
            
            return None
        except Exception as e:
            logger.error(f"User creation error: {e}")
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            user_doc = await self.users_collection.find_one({"id": user_id})
            if user_doc:
                return User(**user_doc)
            return None
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            user_doc = await self.users_collection.find_one({"email": email})
            if user_doc:
                return User(**user_doc)
            return None
        except Exception as e:
            logger.error(f"Get user by email error: {e}")
            return None
    
    async def create_password_reset_token(self, user_id: str) -> str:
        """Generate a single-use reset token and store its hash with expiry."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_reset_token(raw_token)
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

        await self.reset_tokens_collection.update_many(
            {"user_id": user_id, "used_at": None},
            {"$set": {"used_at": now}},
        )

        await self.reset_tokens_collection.insert_one({
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "used_at": None,
            "created_at": now,
        })

        return raw_token

    async def _get_valid_reset_record(self, raw_token: str) -> Optional[dict]:
        """Return a valid, unused, non-expired reset token record."""
        token_hash = self._hash_reset_token(raw_token)
        now = datetime.utcnow()
        return await self.reset_tokens_collection.find_one({
            "token_hash": token_hash,
            "used_at": None,
            "expires_at": {"$gt": now},
        })

    async def validate_reset_token(self, raw_token: str) -> bool:
        """Check whether a reset token is valid."""
        record = await self._get_valid_reset_record(raw_token)
        return record is not None

    async def reset_password(self, raw_token: str, new_password: str) -> bool:
        """Validate token and update the user's password."""
        record = await self._get_valid_reset_record(raw_token)
        if not record:
            return False

        now = datetime.utcnow()
        result = await self.users_collection.update_one(
            {"id": record["user_id"]},
            {"$set": {
                "hashed_password": self.get_password_hash(new_password),
                "updated_at": now,
            }},
        )
        if result.modified_count == 0:
            return False

        await self.reset_tokens_collection.update_one(
            {"_id": record["_id"]},
            {"$set": {"used_at": now}},
        )
        return True

    async def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """Update user profile fields"""
        try:
            update_data = user_update.model_dump(exclude_unset=True)
            if not update_data:
                return await self.get_user_by_id(user_id)

            update_data["updated_at"] = datetime.utcnow()

            result = await self.users_collection.update_one(
                {"id": user_id},
                {"$set": update_data},
            )

            if result.matched_count == 0:
                return None

            return await self.get_user_by_id(user_id)
        except Exception as e:
            logger.error(f"User update error: {e}")
            return None


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = auth_service.verify_token(token)
    if token_data is None:
        raise credentials_exception

    try:
        user = await auth_service.get_user_by_id(token_data.user_id)
    except Exception:
        raise credentials_exception

    if user is None:
        raise credentials_exception

    return user


# Global auth service instance
auth_service = AuthService() 