# app/core/config.py

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    debug: bool = Field(..., alias="DEBUG")
    database_url: str = Field(..., alias="DATABASE_URL")
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")

    # GOOGLE AUTH
    google_client_id: str = Field(..., alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(..., alias="GOOGLE_REDIRECT_URI")
    secret_key_for_session: str = Field(..., alias="SECRET_KEY_FOR_SESSION")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
