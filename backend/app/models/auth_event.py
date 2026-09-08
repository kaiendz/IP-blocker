from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid, utcnow


class AuthEvent(Base):
    """A normalized login attempt pulled from a FortiGate (directly or via FortiCloud)."""

    __tablename__ = "auth_events"
    __table_args__ = (
        Index("ix_auth_events_src_ip_time", "src_ip", "event_time"),
        Index("ix_auth_events_device_time", "device_id", "event_time"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("fortigate_devices.id"), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    src_ip: Mapped[str] = mapped_column(String(64), nullable=False)
    username: Mapped[str] = mapped_column(String(255), default="")
    vpn_type: Mapped[str] = mapped_column(String(32), nullable=False)  # sslvpn | ike | admin
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # failed | success | locked
    reason_text: Mapped[str] = mapped_column(String(500), default="")
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
