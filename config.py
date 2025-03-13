import os
from pathlib import Path
from typing import Optional, Union, Dict, Any

from pydantic import PostgresDsn, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base settings
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "default_secret_key_change_this_in_production"
    APP_NAME: str = "Personal Calendar"
    BASE_DIR: Path = Path(__file__).resolve().parent
    
    # Database
    DB_CONNECTION: str = "sqlite"  # sqlite or postgresql
    SQLITE_DB: str = "calendar.db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "calendar"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    
    # PostgreSQL connection string
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    # JWT Settings
    JWT_SECRET_KEY: str = "jwt_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Notification Settings
    NOTIFICATION_LOG_LEVEL: str = "INFO"
    EMAIL_ENABLED: bool = False
    EMAIL_HOST: Optional[str] = None
    EMAIL_PORT: Optional[int] = None
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    
    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if v:
            return v
        
        if values.get("DB_CONNECTION") == "sqlite":
            sqlite_db_path = values.get("BASE_DIR") / values.get("SQLITE_DB", "calendar.db")
            return f"sqlite:///{sqlite_db_path}"
        
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST"),
            port=str(values.get("POSTGRES_PORT")),
            path=f"/{values.get('POSTGRES_DB', '')}",
        )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Load and export settings
settings = Settings()