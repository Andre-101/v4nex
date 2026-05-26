from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.bridge_status import BridgeStatus
from app.models.time import utc_now


class Bridge(Base):
    __tablename__ = "bridges"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    subdomain: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    public_url: Mapped[str] = mapped_column(String(255), nullable=False)
    target_ipv6: Mapped[str] = mapped_column(String(64), nullable=False)
    target_port: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=BridgeStatus.DRAFT.value, nullable=False)
    last_tcp_validation_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_tcp_validation_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_heartbeat_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    user = relationship("User", back_populates="bridges")
    events = relationship("BridgeEvent", back_populates="bridge", cascade="all, delete-orphan")
