from typing import Any

import httpx

from app.core.config import settings


class CaddyClientError(Exception):
    pass


class CaddyAdminClient:
    def __init__(
        self,
        admin_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.admin_url = (admin_url or settings.caddy_admin_url).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.caddy_admin_timeout_seconds

    def get_current_config(self) -> dict[str, Any]:
        try:
            response = httpx.get(
                f"{self.admin_url}/config/",
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CaddyClientError(str(exc)) from exc

    def load_config(self, config: dict[str, Any]) -> None:
        try:
            response = httpx.post(
                f"{self.admin_url}/load",
                json=config,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CaddyClientError(str(exc)) from exc
