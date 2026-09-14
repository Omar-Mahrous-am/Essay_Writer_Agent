import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    APP_NAME: str = "Essay_Writer"
    MODEL: str = "cohere:command-r-plus-08-2024"
    OPENAI_API_KEY: str = ""
    CO_API_KEY: str = ""
    COHERE_API_KEY: str = ""
    TAVILY_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_cohere_key(self) -> str:
        """Returns CO_API_KEY or COHERE_API_KEY."""
        return self.CO_API_KEY or self.COHERE_API_KEY or os.getenv("CO_API_KEY", "") or os.getenv("COHERE_API_KEY", "")


@lru_cache
def get_settings() -> Settings:
    """Returns a cached instance of application settings."""
    return Settings()


# Singleton instance for quick imports
settings = get_settings()

# Direct convenience exports
APP_NAME = settings.APP_NAME
MODEL = settings.MODEL
OPENAI_API_KEY = settings.OPENAI_API_KEY
CO_API_KEY = settings.get_cohere_key()
TAVILY_API_KEY = settings.TAVILY_API_KEY
