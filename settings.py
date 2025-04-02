from pydantic import BaseSettings


class Settings(BaseSettings):
    PYTHONPATH: str
    QDRANT_HOST: str

    class Config:
        env_file = '.env'
        case_sensitive = True


settings = Settings()
