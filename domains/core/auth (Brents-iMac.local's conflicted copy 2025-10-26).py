"""
Authentication utilities for PiyP
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext

from config.settings import settings


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_refresh_token(user_id: str) -> str:
    """Create a refresh token"""
    data = {
        "sub": user_id,
        "type": "refresh"
    }
    expires_delta = timedelta(days=30)  # Refresh tokens last 30 days
    return create_access_token(data, expires_delta)


def create_password_reset_token(user_id: str) -> str:
    """Create a password reset token"""
    data = {
        "sub": user_id,
        "type": "password_reset"
    }
    expires_delta = timedelta(hours=1)  # Password reset tokens last 1 hour
    return create_access_token(data, expires_delta)


def create_email_verification_token(user_id: str) -> str:
    """Create an email verification token"""
    data = {
        "sub": user_id,
        "type": "email_verification"
    }
    expires_delta = timedelta(days=7)  # Email verification tokens last 7 days
    return create_access_token(data, expires_delta)