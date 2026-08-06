from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str          # postgres://... — conexão DIRETA (não a URL REST do Supabase)
    supabase_jwt_secret: str   # Project Settings > API > JWT Secret
    google_api_key: str = ""
    cors_origins: str = "*"
    max_upload_mb: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
