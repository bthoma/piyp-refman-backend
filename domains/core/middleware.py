"""
Authentication middleware for protected endpoints.
"""

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any

from .auth import verify_token, get_user_profile

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    FastAPI dependency that extracts and verifies JWT.
    Returns the user ID.

    Usage:
        @router.get("/protected")
        async def protected_endpoint(user_id: str = Depends(get_current_user_id)):
            # user_id is verified
            ...
    """
    try:
        token = credentials.credentials
        logger.info(f"Middleware: Extracting token (first 20 chars): {token[:20]}...")
        user_id = verify_token(token)
        logger.info(f"Middleware: Token verified, user_id: {user_id}")
        return user_id
    except Exception as e:
        logger.error(f"Middleware: Token verification failed: {e.__class__.__name__}: {str(e)}")
        raise


async def get_current_user(
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Get full user profile for authenticated user.
    Use when you need more than just the user_id.

    Usage:
        @router.get("/protected")
        async def protected_endpoint(user: dict = Depends(get_current_user)):
            # user contains full profile
            ...
    """
    try:
        logger.info(f"Middleware: Fetching user profile for user_id: {user_id}")
        profile = get_user_profile(user_id)
        logger.info(f"Middleware: Successfully fetched profile for user: {user_id}")
        return profile
    except Exception as e:
        logger.error(f"Middleware: Failed to get user profile: {e.__class__.__name__}: {str(e)}")
        raise


async def require_admin(
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Require authenticated user to be an admin.
    Use for admin-only endpoints.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: dict = Depends(require_admin)):
            # user is verified admin
            ...
    """
    if not user.get('is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return user
