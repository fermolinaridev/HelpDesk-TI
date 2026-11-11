from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://helpdesk:helpdesk@localhost:5432/helpdesk"
    jwt_secret: str = "dev-only-secret-troque-em-producao-0123456789"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    # Fuso usado para agrupar relatórios por mês (o banco guarda tudo em UTC).
    timezone: str = "America/Sao_Paulo"


settings = Settings()
