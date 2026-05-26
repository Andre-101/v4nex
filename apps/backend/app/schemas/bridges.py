from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.domain.bridge_status import BridgeStatus


class BridgeCreateRequest(BaseModel):
    subdomain: str
    target_ipv6: str
    target_port: int


class BridgeResponse(BaseModel):
    id: str
    subdomain: str
    public_url: str
    target_ipv6: str
    target_port: int
    status: BridgeStatus
    last_tcp_validation_at: datetime | None = None
    last_tcp_validation_result: str | None = None
    last_heartbeat_at: datetime | None = None
    last_heartbeat_result: str | None = None
    activated_at: datetime | None = None
    disabled_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BridgeEventResponse(BaseModel):
    id: str
    bridge_id: str
    event_type: str
    message: str
    metadata: dict[str, Any]
    created_at: datetime
