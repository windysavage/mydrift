from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    QDRANT_HOST: str
    MONGODB_HOST: str
    OLLAMA_HOST: str
    OPENAI_API_KEY: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    class Config:
        env_file = ('.env', '.env.dev')
        case_sensitive = True


settings = Settings()
