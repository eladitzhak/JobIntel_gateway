# app/core/config.py

from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    debug: bool = Field(..., alias="DEBUG")
    database_url: str = Field(..., alias="DATABASE_URL")
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
