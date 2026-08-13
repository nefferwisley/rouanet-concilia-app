from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str          # postgres://... — conexão DIRETA (não a URL REST do Supabase)
    supabase_jwt_secret: str   # Legacy JWT Secret (Project Settings > JWT Keys) — fallback pra tokens HS256 antigos
    supabase_url: str = ""     # https://xxxx.supabase.co — usado só pra buscar o JWKS (chaves ES256 novas)
    google_api_key: str = ""
    # Ambiente: "dev" habilita o login de demonstração SEM autenticação
    # (routes/dev_demo.py); qualquer outro valor desabilita a rota.
    app_env: str = "dev"
    # Backend de leitura automática de documentos (P4): "" (auto: Gemini se
    # houver chave, Ollama local caso contrário), "gemini" ou "ollama".
    ocr_backend: str = ""
    cors_origins: str = "*"
    max_upload_mb: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
