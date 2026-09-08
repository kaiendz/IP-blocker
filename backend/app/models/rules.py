from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class DetectionRule(TimestampMixin, Base):
    """'N failures of these event types within M minutes' -> blacklist for TTL hours."""

    __tablename__ = "detection_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), default="global")  # global | device
    device_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("fortigate_devices.id"), nullable=True
    )
    event_types: Mapped[list] = mapped_column(JSON, default=lambda: ["sslvpn", "ike", "admin"])
    threshold_count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    window_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    ttl_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
