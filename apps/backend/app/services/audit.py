from sqlalchemy.orm import Session

from app.models.admin_audit_event import AdminAuditEvent
from app.models.user import User


def add_audit_event(
    db: Session,
    *,
    actor: User,
    action: str,
    message: str,
    metadata: dict | None = None,
    target_user_id: str | None = None,
    bridge_id: str | None = None,
) -> None:
    db.add(
        AdminAuditEvent(
            actor_user_id=actor.id,
            target_user_id=target_user_id,
            bridge_id=bridge_id,
            action=action,
            message=message,
            event_metadata=metadata or {},
        )
    )
