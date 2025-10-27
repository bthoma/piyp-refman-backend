"""
Application Settings for PiyP Backend

Centralized configuration management using Pydantic settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    # Railway uses PORT, local dev uses API_PORT
    api_port: int = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    
    # JWT Configuration
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expiration_minutes: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
    
    # Storage
    pdf_storage_path: str = os.getenv("PDF_STORAGE_PATH", "/tmp/piyp/pdfs")
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    
    # Feature Flags
    enable_rag_search: bool = os.getenv("ENABLE_RAG_SEARCH", "true").lower() == "true"
    enable_hipporag_search: bool = os.getenv("ENABLE_HIPPORAG_SEARCH", "true").lower() == "true"
    enable_ai_ingestion: bool = os.getenv("ENABLE_AI_INGESTION", "true").lower() == "true"
    
    # AI Service Keys (Optional)
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    # Supabase Configuration (Optional - for specific configurations)
    supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
    supabase_anon_key: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
    supabase_service_key: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")

    # Research API Keys (Optional)
    semantic_scholar_api_key: Optional[str] = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    ncbi_api_key: Optional[str] = os.getenv("NCBI_API_KEY")

    # Redis (Upstash) (Optional)
    upstash_redis_rest_url: Optional[str] = os.getenv("UPSTASH_REDIS_REST_URL")
    upstash_redis_rest_token: Optional[str] = os.getenv("UPSTASH_REDIS_REST_TOKEN")

    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings()
