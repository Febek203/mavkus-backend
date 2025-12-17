"""
Configurazione centralizzata
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Firebase
    firebase_project_id: str
    firebase_private_key: str
    firebase_client_email: str
    
    # Encryption
    encryption_key: str
    
    # API Keys (fallback)
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # App
    environment: str = "development"
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()