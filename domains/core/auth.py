"""
Authentication service using Supabase Auth.
Handles signup, login, token verification, and OAuth.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from supabase import Client

from config.database import get_client


class SupabaseAuthService:
    """Service for Supabase authentication operations."""

    @staticmethod
    def signup(email: str, password: str, full_name: str) -> Dict[str, Any]:
        """
        Register a new user with Supabase Auth.

        Args:
            email: User email
            password: User password
            full_name: User's full name

        Returns:
            Dict containing user data and tokens

        Raises:
            HTTPException: If signup fails
        """
        try:
            # Use service key for auth operations to bypass RLS
            auth_client = get_client(use_service_key=True)

            # Sign up with Supabase Auth
            auth_response = auth_client.auth.sign_up({
                "email": email,
                "password": password
            })

            if not auth_response.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user"
                )

            user_id = auth_response.user.id

            # Create profile in core.user_profiles (use service key to bypass RLS)
            profile_data = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "auth_provider": "email",
                "tier": "free",
                "monthly_budget_usd": 10.00,
                "current_month_spent_usd": 0.00,
                "is_admin": False
            }

            profile_result = auth_client.table('user_profiles').insert(profile_data).execute()

            if not profile_result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user profile"
                )

            return {
                "user": {
                    "id": user_id,
                    "email": email,
                    "profile": profile_result.data[0]
                },
                "session": {
                    "access_token": auth_response.session.access_token,
                    "refresh_token": auth_response.session.refresh_token,
                    "expires_in": 3600
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Signup failed: {str(e)}"
            )

    @staticmethod
    def login(email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with Supabase Auth.

        Args:
            email: User email
            password: User password

        Returns:
            Dict containing user data and tokens

        Raises:
            HTTPException: If login fails
        """
        try:
            # Use service key for auth operations
            auth_client = get_client(use_service_key=True)

            # Authenticate with Supabase Auth
            auth_response = auth_client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not auth_response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            user_id = auth_response.user.id

            # Get user profile
            profile_result = auth_client.table('user_profiles').select('*').eq('id', user_id).single().execute()

            if not profile_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found"
                )

            # Update last_login_at
            from datetime import datetime
            auth_client.table('user_profiles').update({
                'last_login_at': datetime.utcnow().isoformat()
            }).eq('id', user_id).execute()

            return {
                "user": {
                    "id": user_id,
                    "email": email,
                    "profile": profile_result.data
                },
                "session": {
                    "access_token": auth_response.session.access_token,
                    "refresh_token": auth_response.session.refresh_token,
                    "expires_in": 3600
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Login failed: {str(e)}"
            )

    @staticmethod
    def verify_token(token: str) -> str:
        """
        Verify JWT token with Supabase Auth.

        Args:
            token: JWT access token

        Returns:
            str: User ID if valid

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            client = get_client()
            user = client.auth.get_user(token)

            if not user or not user.user or not user.user.id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token"
                )

            return user.user.id

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

    @staticmethod
    def get_user_profile(user_id: str) -> Dict[str, Any]:
        """
        Get user profile from database.

        Args:
            user_id: User ID

        Returns:
            Dict containing user profile

        Raises:
            HTTPException: If user not found
        """
        try:
            client = get_client()
            result = client.table('user_profiles').select('*').eq('id', user_id).single().execute()

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found"
                )

            return result.data

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch user profile: {str(e)}"
            )

    @staticmethod
    def refresh_token(refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dict containing new tokens

        Raises:
            HTTPException: If refresh fails
        """
        try:
            client = get_client()

            auth_response = client.auth.set_session(
                access_token="",  # Will be regenerated
                refresh_token=refresh_token
            )

            if not auth_response.session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )

            return {
                "access_token": auth_response.session.access_token,
                "refresh_token": auth_response.session.refresh_token,
                "expires_in": 3600
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token refresh failed"
            )

    @staticmethod
    def logout() -> Dict[str, str]:
        """
        Log out current user (invalidate session).

        Returns:
            Dict with success message
        """
        try:
            client = get_client()
            client.auth.sign_out()
            return {"message": "Successfully logged out"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed"
            )


# Convenience functions
def signup_user(email: str, password: str, full_name: str):
    """Convenience function for user signup."""
    return SupabaseAuthService.signup(email, password, full_name)


def login_user(email: str, password: str):
    """Convenience function for user login."""
    return SupabaseAuthService.login(email, password)


def verify_token(token: str) -> str:
    """Convenience function for token verification."""
    return SupabaseAuthService.verify_token(token)


def get_user_profile(user_id: str):
    """Convenience function to get user profile."""
    return SupabaseAuthService.get_user_profile(user_id)


def refresh_access_token(refresh_token: str):
    """Convenience function to refresh token."""
    return SupabaseAuthService.refresh_token(refresh_token)


def logout_user():
    """Convenience function for logout."""
    return SupabaseAuthService.logout()
