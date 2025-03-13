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

    # Calendar Service Provider
    CALENDAR_SERVICE_PROVIDER: str = "google"  # Options: "google", "apple"

    # Google OAuth Settings
    GOOGLE_CLIENT_SECRETS_FILE: str = "client_secrets.json"
    GOOGLE_OAUTH_SCOPES: list = [
        "https://www.googleapis.com/auth/calendar",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google-auth-callback"
    GOOGLE_CREDENTIALS_DIR: str = "credentials"

    # Ollama LLM Settings
    OLLAMA_ENABLED: bool = True
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_API_ENDPOINT: str = "/v1/chat/completions"
    OLLAMA_TEMPERATURE: float = 0.7
    OLLAMA_MAX_TOKENS: int = 4000
    OLLAMA_TIMEOUT: int = 30  # seconds

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if v:
            return v
        if values.get("DB_CONNECTION") == "sqlite":
            sqlite_db_path = values.get("BASE_DIR") / values.get(
                "SQLITE_DB", "calendar.db"
            )
            return f"sqlite:///{sqlite_db_path}"
        # Manually construct the PostgreSQL connection string
        return (
            f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}"
            f"@{values.get('POSTGRES_HOST')}:{values.get('POSTGRES_PORT')}"
            f"/{values.get('POSTGRES_DB')}"
        )

    @validator("GOOGLE_CLIENT_SECRETS_FILE", pre=True)
    def get_google_client_secrets_path(cls, v: str, values: Dict[str, Any]) -> str:
        """Get the absolute path to the client secrets file"""
        return str(values.get("BASE_DIR") / v)

    @validator("GOOGLE_CREDENTIALS_DIR", pre=True)
    def get_google_credentials_dir(cls, v: str, values: Dict[str, Any]) -> str:
        """Get the absolute path to the credentials directory"""
        credentials_dir = values.get("BASE_DIR") / v
        os.makedirs(credentials_dir, exist_ok=True)
        return str(credentials_dir)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Load and export settings
settings = Settings()
