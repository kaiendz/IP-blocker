import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class BlacklistReason(str, enum.Enum):
    brute_force = "brute_force"
    threat_intel = "threat_intel"
    manual = "manual"


class BlacklistStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    removed = "removed"


class BlacklistEntry(TimestampMixin, Base):
    __tablename__ = "blacklist_entries"
    __table_args__ = (Index("ix_blacklist_ip_status", "ip_or_cidr", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    ip_or_cidr: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_type: Mapped[BlacklistReason] = mapped_column(Enum(BlacklistReason), nullable=False)
    reason_detail: Mapped[str] = mapped_column(String(500), default="")
    source_name: Mapped[str] = mapped_column(String(255), default="")  # threat-intel source name, if any
    device_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("fortigate_devices.id"), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(255), default="system")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[BlacklistStatus] = mapped_column(
        Enum(BlacklistStatus), default=BlacklistStatus.active, nullable=False
    )
    hit_count: Mapped[int] = mapped_column(default=1)
