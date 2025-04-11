# api/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URI: str = "sqlite:///./autogen04202.db"
    API_DOCS: bool = False
    CLEANUP_INTERVAL: int = 300  # 5 minutes
    SESSION_TIMEOUT: int = 3600  # 1 hour
    CONFIG_DIR: str = "configs"  # Default config directory relative to app_root
    DEFAULT_USER_ID: str = "admin@kagent.dev"
    UPGRADE_DATABASE: bool = False

    model_config = {"env_prefix": "AUTOGENSTUDIO_"}


settings = Settings()
