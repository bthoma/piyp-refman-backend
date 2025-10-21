"""
Configuration settings for PiyP Reference Manager Backend.
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # App configuration
    APP_NAME: str = "PiyP Reference Manager API"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "https://piyp-refman.vercel.app",  # Production frontend
    ]
    
    # Railway production overrides
    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins from environment or defaults"""
        cors_env = os.getenv("CORS_ORIGINS")
        if cors_env:
            return [url.strip() for url in cors_env.split(",")]
        return self.ALLOWED_ORIGINS
    
    # Agent configuration
    AGENT_HOST: str = os.getenv("AGENT_HOST", "localhost")
    AGENT_PORT: int = int(os.getenv("AGENT_PORT", "8001"))
    
    # File storage
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "/storage")
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # Task configuration
    TASK_TIMEOUT: int = 3600  # 1 hour
    MAX_CONCURRENT_TASKS: int = 50
    
    # Search configuration
    DEFAULT_SEARCH_LIMIT: int = 20
    MAX_SEARCH_LIMIT: int = 100
    
    # Citation configuration
    SUPPORTED_CITATION_STYLES: List[str] = [
        "apa", "mla", "chicago", "harvard", "vancouver", "ieee", "bibtex"
    ]
    
    # Budget configuration
    DEFAULT_DAILY_BUDGET: float = 20.0  # $20 per day
    INGESTION_COST_PER_PAPER: float = 0.15  # $0.15 per paper
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get application settings (singleton)"""
    global _settings
    
    if _settings is None:
        _settings = Settings()
    
    return _settings