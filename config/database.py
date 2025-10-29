"""
Database Configuration for PiyP Multi-Schema Architecture

This module manages connections to a single Supabase database with multiple schemas:
- core schema: Authentication and user management
- refman schema: Reference manager domain
- research schema: Research agents (future)
- teaching schema: Teaching domain (future)
- writing schema: Writing domain (future)
"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig:
    """Database configuration and client factory"""
    
    def __init__(self):
        # Single Supabase project
        self.url = os.getenv("SUPABASE_URL")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        # Validate required env vars
        self._validate_config()
    
    def _validate_config(self):
        """Ensure all required environment variables are set"""
        required_vars = [
            ("SUPABASE_URL", self.url),
            ("SUPABASE_ANON_KEY", self.anon_key),
            ("SUPABASE_SERVICE_KEY", self.service_key),
        ]
        
        missing = [name for name, value in required_vars if not value]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please ensure .env file has your Supabase credentials."
            )
    
    def get_client(self, use_service_key: bool = False, schema: str = 'public') -> Client:
        """
        Get Supabase client

        Args:
            use_service_key: If True, use service key (bypasses RLS).
                           Use for admin operations only!
            schema: Database schema to use (default: 'public')

        Returns:
            Supabase client connected to the database
        """
        key = self.service_key if use_service_key else self.anon_key

        # Create client with schema options
        options = {
            "schema": schema,
            "headers": {
                "Accept-Profile": schema,
                "Content-Profile": schema
            }
        }

        return create_client(self.url, key, options=options)


# Global database config instance
db_config = DatabaseConfig()


# Convenience functions for getting clients
def get_client(use_service_key: bool = False, schema: str = 'public') -> Client:
    """
    Get Supabase database client

    Usage:
        # For user operations (respects RLS)
        client = get_client()
        papers = client.table('papers').select('*').execute()

        # For admin operations (bypasses RLS)
        admin_client = get_client(use_service_key=True)
        all_papers = admin_client.table('papers').select('*').execute()

        # For core schema operations
        core_client = get_client(use_service_key=True, schema='core')
        profiles = core_client.table('user_profiles').select('*').execute()
    """
    return db_config.get_client(use_service_key, schema)


def get_admin_client() -> Client:
    """Get admin client (bypasses RLS) - use with caution!"""
    return get_client(use_service_key=True)
