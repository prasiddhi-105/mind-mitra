from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


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


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    emergency_contacts: Optional[List[EmergencyContact]] = None
    profile_picture_url: Optional[str] = None


class UserInDB(UserBase):
    id: str
    hashed_password: str
    emergency_contacts: List[EmergencyContact] = []
    is_active: bool = True
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


class MessageResponse(BaseModel):
    message: str


class TokenValidationResponse(BaseModel):
    valid: bool = True 