"""
Core Domain Router - Authentication and User Management
Uses Supabase Auth for authentication.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from typing import Dict, Any

logger = logging.getLogger(__name__)

from config.database import get_client
from .schemas import (
    UserCreate,
    UserLogin,
    AuthResponse,
    Token,
    RefreshTokenRequest,
    ProfileUpdateRequest,
    UserProfile
)
from .auth import (
    signup_user,
    login_user,
    refresh_access_token,
    logout_user,
    initiate_google_oauth,
    handle_oauth_callback,
    exchange_oauth_code
)
from .middleware import get_current_user_id, get_current_user, require_admin

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
async def register(user_data: UserCreate):
    """
    Register a new user with Supabase Auth.
    Creates user in auth.users and profile in core.user_profiles.
    """
    result = signup_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )
    return result


@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin):
    """
    Login user with Supabase Auth.
    Returns JWT tokens and user profile.
    """
    result = login_user(
        email=credentials.email,
        password=credentials.password
    )
    return result


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh an expired access token using refresh token.
    """
    result = refresh_access_token(request.refresh_token)
    return Token(**result)


@router.post("/logout")
async def logout(user_id: str = Depends(get_current_user_id)):
    """
    Logout current user (invalidate session).
    """
    return logout_user()


@router.get("/google")
async def google_auth(request: Request):
    """
    Initiate Google OAuth flow.
    Redirects user to Google's OAuth consent screen.
    """
    # Get the frontend base URL from the request origin or use a default
    origin = request.headers.get("origin", "https://piyp-refman-frontend-production.up.railway.app")
    redirect_url = f"{origin}/auth/callback"

    result = initiate_google_oauth(redirect_url)
    return RedirectResponse(url=result["url"])


@router.get("/auth/callback", response_model=AuthResponse)
async def auth_callback(code: str = None, access_token: str = None, refresh_token: str = None):
    """
    Handle OAuth callback from Supabase.
    Supports both authorization code flow and implicit flow.

    For authorization code flow:
      - Receives 'code' parameter
      - Exchanges code for tokens
      - Creates/updates user profile

    For implicit flow (deprecated, for backward compatibility):
      - Receives 'access_token' and 'refresh_token' parameters
      - Creates/updates user profile directly
    """
    if code:
        # Authorization code flow (preferred)
        result = exchange_oauth_code(code)
        return result
    elif access_token and refresh_token:
        # Implicit flow (deprecated)
        result = handle_oauth_callback(access_token, refresh_token)
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameters: either 'code' or both 'access_token' and 'refresh_token'"
        )


@router.get("/me")
async def get_current_user_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current authenticated user's profile.
    Protected endpoint - requires valid JWT.
    """
    try:
        logger.info(f"GET /me endpoint called for user: {user.get('id', 'unknown')}")
        return {"user": user}
    except Exception as e:
        logger.error(f"Error in GET /me endpoint: {e.__class__.__name__}: {str(e)}")
        logger.exception("Full /me endpoint error:")
        raise


@router.patch("/profile")
async def update_profile(
    updates: ProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update user profile (non-protected fields only).
    Protected fields (tier, monthly_budget_usd, is_admin) require admin.
    """
    client = get_client()

    # Build update dict (only include provided fields)
    update_data = updates.model_dump(exclude_none=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    # Update profile
    result = client.postgrest.schema('core').from_('user_profiles').update(update_data).eq('id', user_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )

    return {"profile": result.data[0]}


# Admin endpoints
@router.get("/admin/users")
async def list_users(
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    List all users (admin only).
    """
    client = get_client()
    result = client.postgrest.schema('core').from_('user_profiles').select('*').execute()

    return {
        "users": result.data,
        "total": len(result.data)
    }


@router.get("/admin/users/{user_id}")
async def get_user(
    user_id: str,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Get specific user details (admin only).
    """
    client = get_client()
    result = client.postgrest.schema('core').from_('user_profiles').select('*').eq('id', user_id).single().execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {"user": result.data}


@router.patch("/admin/users/{user_id}")
async def update_user_admin(
    user_id: str,
    updates: dict,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Update user tier and budget (admin only).
    """
    client = get_client()

    # Validate tier if provided
    if 'tier' in updates:
        valid_tiers = ['free', 'basic', 'pro', 'enterprise']
        if updates['tier'] not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}"
            )

    # Update user
    result = client.postgrest.schema('core').from_('user_profiles').update(updates).eq('id', user_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "message": "User updated successfully",
        "user": result.data[0]
    }
