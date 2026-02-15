from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://portal_user:portal_pass@localhost:5432/rules_review"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "qwen3-embedding:0.6b"
    EMBEDDING_DIMENSIONS: int = 1024
    SIMILARITY_THRESHOLD: float = 0.7

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
