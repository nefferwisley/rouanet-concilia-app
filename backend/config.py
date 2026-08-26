from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str          # postgres://... — conexão DIRETA (não a URL REST do Supabase)
    supabase_jwt_secret: str   # Legacy JWT Secret (Project Settings > JWT Keys) — fallback pra tokens HS256 antigos
    supabase_url: str = ""     # https://xxxx.supabase.co — usado só pra buscar o JWKS (chaves ES256 novas)
    supabase_service_role_key: str = ""  # Service role key pra bypassar RLS no Storage
    google_api_key: str = ""
    # Falha fechada: rotas de desenvolvimento só são habilitadas quando o
    # ambiente é declarado explicitamente como dev/test.
    app_env: str = "production"
    # Backend de leitura automática de documentos (P4): "" (auto: Gemini se
    # houver chave, Ollama local caso contrário), "gemini" ou "ollama".
    ocr_backend: str = ""
    cors_origins: str = "*"
    max_upload_mb: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def dev_routes_enabled(self) -> bool:
        return self.app_env.strip().lower() in {"dev", "test"}


settings = Settings()
