from app.core.config import Settings
from app.core.startup_checks import collect_startup_check_issues


def issue_codes(settings: Settings, environ: dict[str, str] | None = None) -> set[str]:
    return {issue.code for issue in collect_startup_check_issues(settings, environ=environ)}


def test_startup_checks_detect_insecure_jwt_secret_in_non_dev() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret_key="dev-only-change-me",
        database_url="postgresql+psycopg://user:pass@db:5432/v4nex",
        caddy_admin_url="http://caddy:2019",
        public_domain="v4nex.com",
        rate_limit_enabled=True,
    )

    assert "INSECURE_JWT_SECRET_KEY" in issue_codes(
        settings,
        environ={"PUBLIC_DOMAIN": "v4nex.com"},
    )


def test_startup_checks_allow_development_and_test() -> None:
    development_settings = Settings(app_env="development")
    test_settings = Settings(app_env="test", database_url="sqlite:///:memory:")

    assert collect_startup_check_issues(development_settings) == []
    assert collect_startup_check_issues(test_settings) == []


def test_startup_checks_detect_non_dev_sqlite_public_caddy_missing_domain_and_rate_limit() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret_key="real-secret-for-test",
        database_url="sqlite:///local.db",
        caddy_admin_url="http://admin.v4nex.com:2019",
        public_domain="v4nex.com",
        rate_limit_enabled=False,
    )

    codes = issue_codes(settings, environ={})

    assert "SQLITE_DATABASE_URL" in codes
    assert "PUBLIC_CADDY_ADMIN_URL" in codes
    assert "PUBLIC_DOMAIN_NOT_CONFIGURED" in codes
    assert "RATE_LIMIT_DISABLED" in codes
