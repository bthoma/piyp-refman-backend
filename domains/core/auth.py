"""
Authentication service using Supabase Auth.
Handles signup, login, token verification, and OAuth.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from supabase import Client

from config.database import get_client

logger = logging.getLogger(__name__)


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
            auth_client = get_client(use_service_key=True, schema='core')

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

            # Check if session exists (email confirmation may be required)
            if not auth_response.session:
                return {
                    "user": {
                        "id": user_id,
                        "email": email,
                        "profile": profile_result.data[0]
                    },
                    "session": None,
                    "confirmation_required": True,
                    "message": "Signup successful! Please check your email to confirm your account before logging in."
                }

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
                },
                "confirmation_required": False
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
            auth_client = get_client(use_service_key=True, schema='core')

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

            # Get user profile using a fresh service key client to bypass RLS
            # (after sign_in, the auth_client has user session attached)
            profile_client = get_client(use_service_key=True, schema='core')
            profile_result = profile_client.table('user_profiles').select('*').eq('id', user_id).single().execute()

            if not profile_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found"
                )

            # Update last_login_at using the profile client (bypasses RLS)
            from datetime import datetime
            profile_client.table('user_profiles').update({
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
            logger.info(f"Verifying token (first 20 chars): {token[:20]}...")

            # Use service key for token verification to avoid RLS issues
            client = get_client(use_service_key=True)
            logger.info("Getting user from token...")
            user = client.auth.get_user(token)

            logger.info(f"User response: user={user is not None}, user.user={user.user if user else None}")

            if not user or not user.user or not user.user.id:
                logger.error("Token verification failed: No user data returned from Supabase")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token"
                )

            logger.info(f"Token verified successfully for user: {user.user.id}")
            return user.user.id

        except HTTPException as he:
            logger.error(f"HTTPException in verify_token: {he.status_code} - {he.detail}")
            raise
        except Exception as e:
            # Include actual error for debugging
            logger.error(f"Token verification exception: {e.__class__.__name__}: {str(e)}")
            logger.exception("Full token verification error:")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired token: {str(e)}"
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
            logger.info(f"Fetching user profile for user_id: {user_id}")

            # Use service key with core schema to bypass RLS
            client = get_client(use_service_key=True, schema='core')
            logger.info("Executing query on user_profiles table...")
            result = client.table('user_profiles').select('*').eq('id', user_id).single().execute()

            logger.info(f"Query result: data={result.data is not None}, count={result.count if hasattr(result, 'count') else 'N/A'}")

            if not result.data:
                logger.error(f"User profile not found for user_id: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found"
                )

            logger.info(f"Successfully fetched profile for user: {user_id}")
            return result.data

        except HTTPException as he:
            logger.error(f"HTTPException in get_user_profile: {he.status_code} - {he.detail}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch user profile: {e.__class__.__name__}: {str(e)}")
            logger.exception("Full get_user_profile error:")
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

    @staticmethod
    def initiate_google_auth(redirect_url: str) -> Dict[str, str]:
        """
        Initiate Google OAuth flow.

        Args:
            redirect_url: Frontend callback URL to redirect after OAuth

        Returns:
            Dict containing OAuth URL to redirect user to

        Raises:
            HTTPException: If OAuth initiation fails
        """
        try:
            client = get_client(use_service_key=True)

            # Generate OAuth URL
            auth_response = client.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {
                    "redirect_to": redirect_url
                }
            })

            return {
                "url": auth_response.url
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initiate Google OAuth: {str(e)}"
            )

    @staticmethod
    def exchange_oauth_code(code: str) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for tokens.

        Args:
            code: OAuth authorization code from callback

        Returns:
            Dict containing user data and tokens

        Raises:
            HTTPException: If code exchange fails
        """
        try:
            # Use service key client to exchange code
            auth_client = get_client(use_service_key=True, schema='core')

            # Exchange code for session
            session_response = auth_client.auth.exchange_code_for_session({
                "auth_code": code
            })

            if not session_response.session or not session_response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to exchange OAuth code for tokens"
                )

            user = session_response.user
            user_id = user.id
            email = user.email

            # Get or create user profile using fresh service key client
            profile_client = get_client(use_service_key=True, schema='core')

            # Check if profile exists
            existing_profile = profile_client.table('user_profiles').select('*').eq('id', user_id).execute()

            if existing_profile.data and len(existing_profile.data) > 0:
                # Update existing profile
                from datetime import datetime
                profile_result = profile_client.table('user_profiles').update({
                    'last_login_at': datetime.utcnow().isoformat(),
                    'auth_provider': 'google'
                }).eq('id', user_id).execute()

                profile_data = profile_result.data[0]
            else:
                # Create new profile for OAuth user
                full_name = user.user_metadata.get('full_name') or user.user_metadata.get('name') or ''

                profile_data = {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "auth_provider": "google",
                    "tier": "free",
                    "monthly_budget_usd": 10.00,
                    "current_month_spent_usd": 0.00,
                    "is_admin": False
                }

                profile_result = profile_client.table('user_profiles').insert(profile_data).execute()

                if not profile_result.data:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create user profile"
                    )

                profile_data = profile_result.data[0]

            return {
                "user": {
                    "id": user_id,
                    "email": email,
                    "profile": profile_data
                },
                "session": {
                    "access_token": session_response.session.access_token,
                    "refresh_token": session_response.session.refresh_token,
                    "expires_in": 3600
                },
                "confirmation_required": False
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OAuth code exchange failed: {str(e)}"
            )

    @staticmethod
    def handle_oauth_callback(access_token: str, refresh_token: str) -> Dict[str, Any]:
        """
        Handle OAuth callback and create/update user profile.

        Args:
            access_token: OAuth access token from callback
            refresh_token: OAuth refresh token from callback

        Returns:
            Dict containing user data and tokens

        Raises:
            HTTPException: If callback handling fails
        """
        try:
            # Use service key client to set session and get user
            auth_client = get_client(use_service_key=True, schema='core')

            # Set the session with the tokens
            session_response = auth_client.auth.set_session(
                access_token=access_token,
                refresh_token=refresh_token
            )

            if not session_response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to get user from OAuth tokens"
                )

            user = session_response.user
            user_id = user.id
            email = user.email

            # Get or create user profile using fresh service key client
            profile_client = get_client(use_service_key=True, schema='core')

            # Check if profile exists
            existing_profile = profile_client.table('user_profiles').select('*').eq('id', user_id).execute()

            if existing_profile.data and len(existing_profile.data) > 0:
                # Update existing profile
                from datetime import datetime
                profile_result = profile_client.table('user_profiles').update({
                    'last_login_at': datetime.utcnow().isoformat(),
                    'auth_provider': 'google'
                }).eq('id', user_id).execute()

                profile_data = profile_result.data[0]
            else:
                # Create new profile for OAuth user
                full_name = user.user_metadata.get('full_name') or user.user_metadata.get('name') or ''

                profile_data = {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "auth_provider": "google",
                    "tier": "free",
                    "monthly_budget_usd": 10.00,
                    "current_month_spent_usd": 0.00,
                    "is_admin": False
                }

                profile_result = profile_client.table('user_profiles').insert(profile_data).execute()

                if not profile_result.data:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create user profile"
                    )

                profile_data = profile_result.data[0]

            return {
                "user": {
                    "id": user_id,
                    "email": email,
                    "profile": profile_data
                },
                "session": {
                    "access_token": session_response.session.access_token,
                    "refresh_token": session_response.session.refresh_token,
                    "expires_in": 3600
                },
                "confirmation_required": False
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OAuth callback failed: {str(e)}"
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


def initiate_google_oauth(redirect_url: str):
    """Convenience function to initiate Google OAuth."""
    return SupabaseAuthService.initiate_google_auth(redirect_url)


def handle_oauth_callback(access_token: str, refresh_token: str):
    """Convenience function to handle OAuth callback."""
    return SupabaseAuthService.handle_oauth_callback(access_token, refresh_token)


def exchange_oauth_code(code: str):
    """Convenience function to exchange OAuth code."""
    return SupabaseAuthService.exchange_oauth_code(code)
