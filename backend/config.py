from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str          # postgres://... — conexão DIRETA (não a URL REST do Supabase)
    supabase_jwt_secret: str   # Legacy JWT Secret (Project Settings > JWT Keys) — fallback pra tokens HS256 antigos
    supabase_url: str = ""     # https://xxxx.supabase.co — usado só pra buscar o JWKS (chaves ES256 novas)
    google_api_key: str = ""
    cors_origins: str = "*"
    max_upload_mb: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
