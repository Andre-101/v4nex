from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlparse

from app.core.config import Settings


SAFE_CADDY_ADMIN_HOSTS = {"caddy", "localhost"}


@dataclass(frozen=True)
class StartupCheckIssue:
    code: str
    message: str


class StartupCheckError(RuntimeError):
    def __init__(self, issues: list[StartupCheckIssue]) -> None:
        self.issues = issues
        super().__init__("Startup configuration checks failed.")


def is_development_like(app_env: str) -> bool:
    return app_env.lower() in {"development", "dev", "test", "testing"}


def _caddy_admin_url_looks_public(caddy_admin_url: str) -> bool:
    parsed = urlparse(caddy_admin_url)
    host = parsed.hostname
    if host is None:
        return True

    normalized = host.strip().lower()
    if normalized in SAFE_CADDY_ADMIN_HOSTS:
        return False

    try:
        parsed_ip = ip_address(normalized)
    except ValueError:
        # Docker service names are acceptable for local/private control-plane access.
        return "." in normalized

    return not (parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_link_local)


def collect_startup_check_issues(
    settings: Settings,
    environ: dict[str, str] | None = None,
) -> list[StartupCheckIssue]:
    env = environ or {}
    if is_development_like(settings.app_env):
        return []

    issues: list[StartupCheckIssue] = []
    if settings.jwt_secret_key == "dev-only-change-me":
        issues.append(
            StartupCheckIssue(
                code="INSECURE_JWT_SECRET_KEY",
                message="JWT_SECRET_KEY must not use the development default outside dev/test.",
            )
        )

    if settings.database_url.startswith("sqlite"):
        issues.append(
            StartupCheckIssue(
                code="SQLITE_DATABASE_URL",
                message="DATABASE_URL must not use SQLite outside dev/test.",
            )
        )

    if _caddy_admin_url_looks_public(settings.caddy_admin_url):
        issues.append(
            StartupCheckIssue(
                code="PUBLIC_CADDY_ADMIN_URL",
                message="CADDY_ADMIN_URL must point to Docker/internal/localhost access only.",
            )
        )

    if not settings.public_domain or not env.get("PUBLIC_DOMAIN"):
        issues.append(
            StartupCheckIssue(
                code="PUBLIC_DOMAIN_NOT_CONFIGURED",
                message="PUBLIC_DOMAIN must be explicitly configured outside dev/test.",
            )
        )

    if not settings.rate_limit_enabled:
        issues.append(
            StartupCheckIssue(
                code="RATE_LIMIT_DISABLED",
                message="RATE_LIMIT_ENABLED must be true outside dev/test.",
            )
        )

    return issues


def assert_startup_checks(settings: Settings, environ: dict[str, str] | None = None) -> None:
    issues = collect_startup_check_issues(settings, environ=environ)
    if issues:
        raise StartupCheckError(issues)
