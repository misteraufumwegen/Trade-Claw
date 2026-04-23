"""
Configuration management for Trade-Claw backend
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # API Configuration
    API_TITLE: str = "Trade-Claw API"
    API_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
    ]
    
    # Database
    DATABASE_URL: str = "postgresql://tradeuser:tradepass@postgres:5432/tradeclaw"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    
    # OANDA
    OANDA_API_KEY: str = ""
    OANDA_ACCOUNT_ID: str = ""
    OANDA_ENV: str = "v20"  # practice or live
    
    # Data Sources
    DATA_SOURCE: str = "oanda"  # oanda or yfinance
    FALLBACK_TO_YFINANCE: bool = True
    
    # Backtest
    BACKTEST_DATA_DIR: str = "/data/backtest"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
