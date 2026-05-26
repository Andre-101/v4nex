import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "v4nex-backend"
    app_env: str = "development"
    internal_api_prefix: str = "/_v4nex"
    public_domain: str = "v4nex.com"
    database_url: str = "postgresql+psycopg://v4nex:devpassword@db:5432/v4nex"
    jwt_secret_key: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", os.getenv("ENV", Settings.model_fields["app_env"].default)),
        database_url=os.getenv("DATABASE_URL", Settings.model_fields["database_url"].default),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", Settings.model_fields["jwt_secret_key"].default),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", Settings.model_fields["jwt_algorithm"].default),
        access_token_expire_minutes=int(
            os.getenv(
                "ACCESS_TOKEN_EXPIRE_MINUTES",
                str(Settings.model_fields["access_token_expire_minutes"].default),
            )
        ),
    )


settings = get_settings()
