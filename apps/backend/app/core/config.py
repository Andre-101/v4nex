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
    max_bridges_per_user: int = 5
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 30
    rate_limit_strict_max_requests: int = 10
    allowed_target_ports: tuple[int, ...] = (80, 8080)


def get_settings() -> Settings:
    allowed_target_ports = tuple(
        int(port.strip())
        for port in os.getenv(
            "ALLOWED_TARGET_PORTS",
            ",".join(str(port) for port in Settings.model_fields["allowed_target_ports"].default),
        ).split(",")
        if port.strip()
    )

    return Settings(
        app_env=os.getenv("APP_ENV", os.getenv("ENV", Settings.model_fields["app_env"].default)),
        public_domain=os.getenv(
            "PUBLIC_DOMAIN",
            Settings.model_fields["public_domain"].default,
        ),
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
        max_bridges_per_user=int(
            os.getenv(
                "MAX_BRIDGES_PER_USER",
                str(Settings.model_fields["max_bridges_per_user"].default),
            )
        ),
        rate_limit_enabled=os.getenv(
            "RATE_LIMIT_ENABLED",
            str(Settings.model_fields["rate_limit_enabled"].default),
        ).lower()
        in {"1", "true", "yes", "on"},
        rate_limit_window_seconds=int(
            os.getenv(
                "RATE_LIMIT_WINDOW_SECONDS",
                str(Settings.model_fields["rate_limit_window_seconds"].default),
            )
        ),
        rate_limit_max_requests=int(
            os.getenv(
                "RATE_LIMIT_MAX_REQUESTS",
                str(Settings.model_fields["rate_limit_max_requests"].default),
            )
        ),
        rate_limit_strict_max_requests=int(
            os.getenv(
                "RATE_LIMIT_STRICT_MAX_REQUESTS",
                str(Settings.model_fields["rate_limit_strict_max_requests"].default),
            )
        ),
        allowed_target_ports=allowed_target_ports,
    )


settings = get_settings()
