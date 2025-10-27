"""
Pydantic schemas for Core domain (Authentication).
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import re


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str
    full_name: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain number')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for authentication tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


class UserProfile(BaseModel):
    """Schema for user profile."""
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    auth_provider: str = "email"
    last_login_at: Optional[datetime] = None
    tier: str = "free"
    is_admin: bool = False
    monthly_budget_usd: float = 10.00
    current_month_spent_usd: float = 0.00
    budget_alert_threshold: float = 0.80
    timezone: str = "UTC"
    default_citation_style: str = "apa"
    ai_features_enabled: bool = True
    auto_ingest_uploads: bool = False
    rag_search_enabled: bool = True
    kg_search_enabled: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Schema for user response."""
    id: str
    email: EmailStr
    profile: UserProfile


class AuthResponse(BaseModel):
    """Schema for authentication response."""
    user: dict
    session: dict


class ProfileUpdateRequest(BaseModel):
    """Schema for profile update request."""
    full_name: Optional[str] = None
    timezone: Optional[str] = None
    default_citation_style: Optional[str] = None
    ai_features_enabled: Optional[bool] = None
    auto_ingest_uploads: Optional[bool] = None
    rag_search_enabled: Optional[bool] = None
    kg_search_enabled: Optional[bool] = None
