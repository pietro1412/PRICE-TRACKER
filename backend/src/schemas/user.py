"""User schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for user update."""

    full_name: str | None = None
    password: str | None = Field(None, min_length=8)


class UserResponse(UserBase):
    """Schema for user response."""

    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str
    exp: datetime
    type: str


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str
