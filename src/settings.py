from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str
    QDRANT_HOST: str
    MONGODB_HOST: str
    OLLAMA_HOST: str
    OPENAI_API_KEY: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    model_config = SettingsConfigDict(
        env_file=('.env', '.env.dev'), env_file_encoding='utf-8', case_sensitive=True
    )


def get_settings() -> BaseSettings:
    return Settings()
