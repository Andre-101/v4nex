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
    caddy_admin_url: str = "http://caddy:2019"
    caddy_admin_timeout_seconds: float = 3.0


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
        caddy_admin_url=os.getenv(
            "CADDY_ADMIN_URL",
            Settings.model_fields["caddy_admin_url"].default,
        ),
        caddy_admin_timeout_seconds=float(
            os.getenv(
                "CADDY_ADMIN_TIMEOUT_SECONDS",
                str(Settings.model_fields["caddy_admin_timeout_seconds"].default),
            )
        ),
    )


settings = get_settings()
