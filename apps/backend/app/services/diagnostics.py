from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.bridge_status import BridgeStatus
from app.models.bridge import Bridge
from app.services.caddy_client import CaddyAdminClient, CaddyClientError


def database_url_driver(database_url: str) -> str:
    parsed = urlparse(database_url)
    return parsed.scheme or "unknown"


def is_caddy_admin_reachable() -> bool:
    try:
        CaddyAdminClient().get_current_config()
    except CaddyClientError:
        return False
    return True


def build_diagnostics(db: Session) -> dict:
    active_count = db.scalar(
        select(func.count()).select_from(Bridge).where(Bridge.status == BridgeStatus.ACTIVE.value)
    )
    return {
        "app_env": settings.app_env,
        "public_domain": settings.public_domain,
        "caddy_admin_url": settings.caddy_admin_url,
        "database_url_driver": database_url_driver(settings.database_url),
        "caddy_admin_reachable": is_caddy_admin_reachable(),
        "active_bridges_count": active_count or 0,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "max_bridges_per_user": settings.max_bridges_per_user,
        "admin_endpoints_protected": True,
    }
