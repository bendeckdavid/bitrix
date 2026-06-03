from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App Local OAuth
    bitrix_client_id: str = ""
    bitrix_client_secret: str = ""

    # URL pública
    app_base_url: str = ""

    # Quantum Backend
    quantum_url: str = ""
    quantum_api_key: str = ""

    # OpenAI
    openai_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
