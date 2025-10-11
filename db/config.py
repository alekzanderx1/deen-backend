# db/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices
from sqlalchemy.engine import URL

class Settings(BaseSettings):
    # Load .env but DO ignore anything extra in your environment
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Accept multiple common env names for flexibility
    DB_USER: str = Field(
        validation_alias=AliasChoices("DB_USER", "POSTGRES_USER", "PGUSER"),
    )
    DB_PASSWORD: str = Field(
        validation_alias=AliasChoices("DB_PASSWORD", "POSTGRES_PASSWORD", "PGPASSWORD"),
    )
    DB_HOST: str = Field(
        validation_alias=AliasChoices("DB_HOST", "POSTGRES_HOST", "PGHOST"),
    )
    DB_PORT: int = Field(
        validation_alias=AliasChoices("DB_PORT", "POSTGRES_PORT", "PGPORT"),
    )
    DB_NAME: str = Field(
        validation_alias=AliasChoices("DB_NAME", "POSTGRES_DB", "PGDATABASE", "DATABASE_NAME"),
    )

    @property
    def DATABASE_URL(self) -> str:
        # Use URL.create to properly escape special characters in username/password
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        ).render_as_string(hide_password=False)

settings = Settings()
