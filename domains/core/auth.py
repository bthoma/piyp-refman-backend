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

            profile_result = auth_client.postgrest.schema('core').from_('user_profiles').insert(profile_data).execute()

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

            # Get user profile using a fresh service key client to bypass RLS
            # (after sign_in, the auth_client has user session attached)
            profile_client = get_client(use_service_key=True)
            profile_result = profile_client.postgrest.schema('core').from_('user_profiles').select('*').eq('id', user_id).single().execute()

            if not profile_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found"
                )

            # Update last_login_at using the profile client (bypasses RLS)
            from datetime import datetime
            profile_client.postgrest.schema('core').from_('user_profiles').update({
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
            client = get_client(use_service_key=True)
            logger.info("Executing query on user_profiles table in core schema...")
            result = client.postgrest.schema('core').from_('user_profiles').select('*').eq('id', user_id).single().execute()

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
        logger.info("=" * 80)
        logger.info("OAUTH: exchange_oauth_code() CALLED")
        logger.info(f"OAUTH: Authorization code (first 20 chars): {code[:20]}...")
        logger.info("=" * 80)

        try:
            # Use service key client to exchange code
            logger.info("OAUTH: Creating service key client for code exchange...")
            auth_client = get_client(use_service_key=True)

            # Exchange code for session
            logger.info("OAUTH: Exchanging authorization code for session...")
            session_response = auth_client.auth.exchange_code_for_session({
                "auth_code": code
            })
            logger.info(f"OAUTH: Code exchange response received. Session exists: {session_response.session is not None}, User exists: {session_response.user is not None}")

            if not session_response.session or not session_response.user:
                logger.error("OAUTH: Code exchange failed - no session or user returned")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to exchange OAuth code for tokens"
                )

            user = session_response.user
            user_id = user.id
            email = user.email
            logger.info(f"OAUTH: Successfully exchanged code. User ID: {user_id}, Email: {email}")
            logger.info(f"OAUTH: User metadata: {user.user_metadata}")

            # Get or create user profile using fresh service key client
            logger.info("OAUTH: Creating fresh service key client for profile operations...")
            profile_client = get_client(use_service_key=True)

            # Check if profile exists
            logger.info(f"OAUTH: Checking if profile exists for user_id: {user_id}")
            existing_profile = profile_client.postgrest.schema('core').from_('user_profiles').select('*').eq('id', user_id).execute()
            logger.info(f"OAUTH: Profile check result - data exists: {existing_profile.data is not None}, count: {len(existing_profile.data) if existing_profile.data else 0}")

            if existing_profile.data and len(existing_profile.data) > 0:
                # Update existing profile
                logger.info("OAUTH: Profile exists, updating last_login_at and auth_provider...")
                from datetime import datetime
                update_data = {
                    'last_login_at': datetime.utcnow().isoformat(),
                    'auth_provider': 'google'
                }
                logger.info(f"OAUTH: Update data: {update_data}")
                profile_result = profile_client.postgrest.schema('core').from_('user_profiles').update(update_data).eq('id', user_id).execute()
                logger.info(f"OAUTH: Profile update complete. Result data: {profile_result.data}")

                profile_data = profile_result.data[0]
                logger.info(f"OAUTH: Using existing profile for user: {user_id}")
            else:
                # Create new profile for OAuth user
                logger.info("OAUTH: No existing profile found, creating new profile...")
                full_name = user.user_metadata.get('full_name') or user.user_metadata.get('name') or ''
                logger.info(f"OAUTH: Extracted full_name from metadata: '{full_name}'")

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
                logger.info(f"OAUTH: Profile data to insert: {profile_data}")

                logger.info("OAUTH: Executing INSERT into core.user_profiles...")
                profile_result = profile_client.postgrest.schema('core').from_('user_profiles').insert(profile_data).execute()
                logger.info(f"OAUTH: INSERT result - data exists: {profile_result.data is not None}, data: {profile_result.data}")

                if not profile_result.data:
                    logger.error("OAUTH: Profile creation failed - INSERT returned no data")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create user profile"
                    )

                profile_data = profile_result.data[0]
                logger.info(f"OAUTH: Successfully created new profile for user: {user_id}")

            logger.info("OAUTH: Building response with user data and session tokens...")
            response = {
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
            logger.info("OAUTH: exchange_oauth_code() COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            return response

        except HTTPException as he:
            logger.error(f"OAUTH: HTTPException in exchange_oauth_code: {he.status_code} - {he.detail}")
            logger.exception("OAUTH: Full HTTPException traceback:")
            raise
        except Exception as e:
            logger.error(f"OAUTH: Exception in exchange_oauth_code: {e.__class__.__name__}: {str(e)}")
            logger.exception("OAUTH: Full exception traceback:")
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
        logger.info("=" * 80)
        logger.info("OAUTH: handle_oauth_callback() CALLED")
        logger.info(f"OAUTH: Access token (first 20 chars): {access_token[:20]}...")
        logger.info(f"OAUTH: Refresh token (first 20 chars): {refresh_token[:20]}...")
        logger.info("=" * 80)

        try:
            # Use service key client to set session and get user
            logger.info("OAUTH: Creating service key client for session setup...")
            auth_client = get_client(use_service_key=True)

            # Set the session with the tokens
            logger.info("OAUTH: Setting session with provided tokens...")
            session_response = auth_client.auth.set_session(
                access_token=access_token,
                refresh_token=refresh_token
            )
            logger.info(f"OAUTH: Session set. User exists: {session_response.user is not None}")

            if not session_response.user:
                logger.error("OAUTH: Failed to get user from tokens")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to get user from OAuth tokens"
                )

            user = session_response.user
            user_id = user.id
            email = user.email
            logger.info(f"OAUTH: Successfully retrieved user from tokens. User ID: {user_id}, Email: {email}")
            logger.info(f"OAUTH: User metadata: {user.user_metadata}")

            # Get or create user profile using fresh service key client
            logger.info("OAUTH: Creating fresh service key client for profile operations...")
            profile_client = get_client(use_service_key=True)

            # Check if profile exists
            logger.info(f"OAUTH: Checking if profile exists for user_id: {user_id}")
            existing_profile = profile_client.postgrest.schema('core').from_('user_profiles').select('*').eq('id', user_id).execute()
            logger.info(f"OAUTH: Profile check result - data exists: {existing_profile.data is not None}, count: {len(existing_profile.data) if existing_profile.data else 0}")

            if existing_profile.data and len(existing_profile.data) > 0:
                # Update existing profile
                logger.info("OAUTH: Profile exists, updating last_login_at and auth_provider...")
                from datetime import datetime
                update_data = {
                    'last_login_at': datetime.utcnow().isoformat(),
                    'auth_provider': 'google'
                }
                logger.info(f"OAUTH: Update data: {update_data}")
                profile_result = profile_client.postgrest.schema('core').from_('user_profiles').update(update_data).eq('id', user_id).execute()
                logger.info(f"OAUTH: Profile update complete. Result data: {profile_result.data}")

                profile_data = profile_result.data[0]
                logger.info(f"OAUTH: Using existing profile for user: {user_id}")
            else:
                # Create new profile for OAuth user
                logger.info("OAUTH: No existing profile found, creating new profile...")
                full_name = user.user_metadata.get('full_name') or user.user_metadata.get('name') or ''
                logger.info(f"OAUTH: Extracted full_name from metadata: '{full_name}'")

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
                logger.info(f"OAUTH: Profile data to insert: {profile_data}")

                logger.info("OAUTH: Executing INSERT into core.user_profiles...")
                profile_result = profile_client.postgrest.schema('core').from_('user_profiles').insert(profile_data).execute()
                logger.info(f"OAUTH: INSERT result - data exists: {profile_result.data is not None}, data: {profile_result.data}")

                if not profile_result.data:
                    logger.error("OAUTH: Profile creation failed - INSERT returned no data")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create user profile"
                    )

                profile_data = profile_result.data[0]
                logger.info(f"OAUTH: Successfully created new profile for user: {user_id}")

            logger.info("OAUTH: Building response with user data and session tokens...")
            response = {
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
            logger.info("OAUTH: handle_oauth_callback() COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            return response

        except HTTPException as he:
            logger.error(f"OAUTH: HTTPException in handle_oauth_callback: {he.status_code} - {he.detail}")
            logger.exception("OAUTH: Full HTTPException traceback:")
            raise
        except Exception as e:
            logger.error(f"OAUTH: Exception in handle_oauth_callback: {e.__class__.__name__}: {str(e)}")
            logger.exception("OAUTH: Full exception traceback:")
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
