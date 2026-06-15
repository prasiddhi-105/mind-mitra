from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator
import re
from typing import List, Optional
from datetime import datetime
from enum import Enum


def validate_password_complexity(password: str) -> None:
    """Validate general password complexity: uppercase, lowercase, digit, symbol, sequences."""
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r'[0-9]', password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character.")

    # Repeated characters like aaaaa
    if re.search(r'(.)\1{4,}', password):
        raise ValueError("Password must not contain repeated characters (e.g., 'aaaaa').")

    # Common sequences
    sequential_patterns = ["12345", "54321", "abcde", "qwerty"]
    for pattern in sequential_patterns:
        if pattern in password.lower():
            raise ValueError(f"Password must not contain common sequences like '{pattern}'.")


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    THERAPIST = "therapist"


class EmergencyContact(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    relationship: str = Field(..., min_length=1, max_length=50)


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

    @model_validator(mode="after")
    def validate_password(self) -> 'UserCreate':
        validate_password_complexity(self.password)
        
        name_lower = self.name.lower()
        email_prefix = self.email.split('@')[0].lower()
        password_lower = self.password.lower()

        if name_lower in password_lower:
            raise ValueError("Password must not contain your name.")
        if email_prefix in password_lower:
            raise ValueError("Password must not contain your email prefix.")
        
        return self


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    emergency_contacts: Optional[List[EmergencyContact]] = None
    profile_picture_url: Optional[str] = None


class UserInDB(UserBase):
    id: str
    hashed_password: str
    emergency_contacts: List[EmergencyContact] = []
    is_active: bool = True
    last_sos_sent: Optional[datetime] = None  # Added for 30-min cooldown tracking
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class User(BaseModel):
    """Public user representation — no password fields exposed."""
    id: str
    email: str
    name: str
    role: UserRole
    is_active: bool = True
    emergency_contacts: List[EmergencyContact] = []
    profile_picture_url: Optional[str] = None
    depression_threshold_notified_at: Optional[datetime] = None
    last_sos_sent: Optional[datetime] = None  # Added for 30-min cooldown tracking
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    expires_in: int


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[UserRole] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        validate_password_complexity(v)
        return v


class MessageResponse(BaseModel):
    message: str


class TokenValidationResponse(BaseModel):
    valid: bool = True
