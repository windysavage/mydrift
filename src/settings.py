from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    QDRANT_HOST: str
    MONGODB_HOST: str
    OLLAMA_HOST: str

    class Config:
        env_file = '.env'
        case_sensitive = True


settings = Settings()
