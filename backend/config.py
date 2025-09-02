from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Defaults are safe for local development with SQLite.
    """

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "sqlite:///./rules.db"

    default_locale: str = "es-ES"

    max_recs_per_day: int = 3
    max_recs_per_category_per_day: int = 1


settings = Settings()


