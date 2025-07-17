from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./payroll.db"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # App settings
    app_name: str = "Payroll Backend"
    debug: bool = True
    
    # Telegram Bot (if needed)
    telegram_bot_token: Optional[str] = None
    telegram_webhook_url: Optional[str] = None
    
    # Auth0 settings
    auth0_domain: Optional[str] = None
    auth0_audience: Optional[str] = None
    
    class Config:
        env_file = ".env"


settings = Settings()