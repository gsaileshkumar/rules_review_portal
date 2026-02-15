from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://portal_user:portal_pass@localhost:5432/rules_review"

    class Config:
        env_file = ".env"


settings = Settings()
