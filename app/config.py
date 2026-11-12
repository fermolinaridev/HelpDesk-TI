from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-secret-troque-em-producao-0123456789"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://helpdesk:helpdesk@localhost:5432/helpdesk"
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    # Fuso usado para agrupar relatórios por mês (o banco guarda tudo em UTC).
    timezone: str = "America/Sao_Paulo"
    # Triagem por IA. Sem chave, o sistema usa só o classificador por palavras-chave.
    anthropic_api_key: str = ""
    triage_model: str = "claude-opus-5-5"
    # Build do front servido por app.web (deploy em um contêiner só).
    frontend_dist: str = "frontend/dist"

    @field_validator("database_url")
    @classmethod
    def _usar_psycopg(cls, url: str) -> str:
        """Plataformas como Render e Heroku entregam postgres:// ou postgresql://.
        O SQLAlchemy precisa saber o driver: postgresql+psycopg://."""
        for prefixo in ("postgres://", "postgresql://"):
            if url.startswith(prefixo):
                return "postgresql+psycopg://" + url.removeprefix(prefixo)
        return url


settings = Settings()
